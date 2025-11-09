import os
import struct
from typing import List, Tuple


class LZStarArchiver:
    def __init__(self):
        pass
    
    def compress(self, input_file: str, output_file: str, window_size: int = 4096) -> bool:
        try:
            if not os.path.exists(input_file):
                print(f"Ошибка: файл '{input_file}' не существует!")
                return False
            
            with open(input_file, 'rb') as f:
                data = f.read()
            
            print(f"Чтение файла: {len(data)} байт")
            
            # Определяем тип файла для оптимизации параметров
            file_ext = os.path.splitext(input_file)[1].lower()
            is_binary = file_ext in ['.bmp', '.exe', '.dll', '.bin']
            
            # Проверяем, является ли файл BMP по сигнатуре
            is_bmp_file = len(data) >= 2 and data[:2] == b'BM'
            
            compressed_nodes = self._compress_data(data, window_size, is_binary, is_bmp_file)
            
            with open(output_file, 'wb') as f:
                # Улучшенный заголовок с контрольной суммой
                header = struct.pack('<4sIII', b'LZ*1', window_size, len(data), self._simple_checksum(data))
                f.write(header)
                
                f.write(struct.pack('<I', len(compressed_nodes)))
                
                for node in compressed_nodes:
                    f.write(struct.pack('<HHB', node[0], node[1], node[2]))
            
            # Статистика
            original_size = len(data)
            compressed_size = os.path.getsize(output_file)
            compression_ratio = compressed_size / original_size if original_size > 0 else 0
            
            print("=" * 50)
            print("СЖАТИЕ ЗАВЕРШЕНО УСПЕШНО!")
            print(f"Исходный файл: {input_file}")
            print(f"Сжатый файл: {output_file}")
            print(f"Исходный размер: {original_size} байт")
            print(f"Размер после сжатия: {compressed_size} байт")
            print(f"Коэффициент сжатия: {compression_ratio:.2f}")
           
            return True
            
        except Exception as e:
            print(f"Ошибка при сжатии: {e}")
            return False
    
    def decompress(self, input_file: str, output_file: str) -> bool:
        try:
            if not os.path.exists(input_file):
                print(f"Ошибка: файл '{input_file}' не существует!")
                return False
            
            with open(input_file, 'rb') as f:
                header = f.read(16)
                if len(header) < 16:
                    print("Ошибка: файл слишком короткий или поврежден!")
                    return False
                
                signature, window_size, original_size, checksum = struct.unpack('<4sIII', header)
                
                if signature != b'LZ*1':
                    print("Ошибка: неверный формат файла!")
                    return False
                
                nodes_count_data = f.read(4)
                if len(nodes_count_data) < 4:
                    print("Ошибка: файл поврежден!")
                    return False
                
                nodes_count = struct.unpack('<I', nodes_count_data)[0]
                
                compressed_nodes = []
                for _ in range(nodes_count):
                    node_data = f.read(5)
                    if len(node_data) < 5:
                        print("Ошибка: файл поврежден!")
                        return False
                    
                    offset, length, next_byte = struct.unpack('<HHB', node_data)
                    compressed_nodes.append((offset, length, next_byte))
            
            decompressed_data = self._decompress_data(compressed_nodes, original_size)
            
            # Проверка целостности
            if len(decompressed_data) != original_size:
                print(f"Ошибка: размер восстановленных данных ({len(decompressed_data)}) не совпадает с ожидаемым ({original_size})")
                return False
            
            # Проверка контрольной суммы
            if self._simple_checksum(decompressed_data) != checksum:
                print("Предупреждение: контрольная сумма не совпадает! Файл может быть поврежден.")
            
            # Проверка для BMP файлов
            if output_file.lower().endswith('.bmp'):
                if not self._validate_bmp(decompressed_data):
                    print("Предупреждение: распакованные данные не являются валидным BMP файлом!")
            
            with open(output_file, 'wb') as f:
                f.write(decompressed_data)
            
            print("=" * 50)
            print("РАСПАКОВКА ЗАВЕРШЕНА УСПЕШНО!")
            print(f"Сжатый файл: {input_file}")
            print(f"Восстановленный файл: {output_file}")
            print(f"Размер восстановленных данных: {len(decompressed_data)} байт")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при распаковке: {e}")
            return False
    
    def _compress_data(self, data: bytes, window_size: int, is_binary: bool = False, is_bmp: bool = False) -> List[Tuple[int, int, int]]:
        result = []
        pos = 0
        data_len = len(data)
        
        window_size = min(window_size, 65535)
        
        # Оптимизация параметров для разных типов данных
        if is_bmp:
            # Для BMP файлов используем более осторожные параметры
            min_match_length = 2  # Уменьшаем минимальную длину совпадения
            max_length = 255
            strict_binary_check = False  # Не пропускаем короткие совпадения
        elif is_binary:
            min_match_length = 4
            max_length = 65535
            strict_binary_check = True
        else:
            min_match_length = 3
            max_length = 255
            strict_binary_check = False
        
        while pos < data_len:
            best_offset, best_length = self._find_best_match(data, pos, window_size, max_length)
            
            if best_length >= min_match_length:
                # Для бинарных данных более строгая проверка (кроме BMP)
                if strict_binary_check and best_length < 6:
                    # Для бинарных данных требуем более длинные совпадения
                    result.append((0, 0, data[pos]))
                    pos += 1
                else:
                    next_byte = data[pos + best_length] if pos + best_length < data_len else 0
                    result.append((best_offset, best_length, next_byte))
                    pos += best_length + 1
            else:
                result.append((0, 0, data[pos]))
                pos += 1
        
        return result
    
    def _find_best_match(self, data: bytes, pos: int, window_size: int, max_length: int) -> Tuple[int, int]:
        best_offset = 0
        best_length = 0
        
        if pos == 0:
            return best_offset, best_length
        
        search_start = max(0, pos - window_size)
        current_max_length = min(max_length, len(data) - pos)
        
        # Оптимизация: начинаем поиск с ближайших позиций
        for i in range(pos - 1, search_start - 1, -1):
            length = 0
            
            while (length < current_max_length and 
                   i + length < pos and 
                   pos + length < len(data) and 
                   data[i + length] == data[pos + length]):
                length += 1
            
            if length > best_length:
                best_length = length
                best_offset = pos - i
                # Если нашли идеальное совпадение, выходим раньше
                if best_length == current_max_length:
                    break
        
        return best_offset, best_length
    
    def _decompress_data(self, compressed_nodes: List[Tuple[int, int, int]], original_size: int) -> bytes:
        result = bytearray()
        
        for node in compressed_nodes:
            if len(result) >= original_size:
                break
                
            offset, length, next_byte = node
            
            if length == 0:
                # Всегда добавляем байт, даже если он нулевой
                result.append(next_byte)
            else:
                start_pos = len(result) - offset
                
                if start_pos < 0 or start_pos >= len(result):
                    print("Ошибка: некорректное смещение при распаковке!")
                    # В случае ошибки добавляем как обычный байт
                    result.append(next_byte)
                    continue
                
                # Копируем последовательность
                for i in range(length):
                    if len(result) >= original_size:
                        break
                    if start_pos + i < len(result):
                        result.append(result[start_pos + i])
                    else:
                        # Если вышли за границы, заполняем нулями
                        result.append(0)
                
                # ВАЖНОЕ ИСПРАВЛЕНИЕ: Всегда добавляем следующий байт, включая нулевые
                if len(result) < original_size:
                    result.append(next_byte)
        
        # Добиваем до нужного размера, если не хватило данных
        while len(result) < original_size:
            result.append(0)
        
        return bytes(result[:original_size])
    
    def _simple_checksum(self, data: bytes) -> int:
        """Простая контрольная сумма для проверки целостности"""
        checksum = 0
        for byte in data:
            checksum = (checksum + byte) & 0xFFFFFFFF
        return checksum
    
    def _validate_bmp(self, data: bytes) -> bool:
        """Расширенная проверка валидности BMP файла"""
        if len(data) < 54:  # Минимальный размер для BMP с заголовком
            return False
        
        # Проверка сигнатуры BMP
        if data[:2] != b'BM':
            return False
        
        try:
            file_size = struct.unpack('<I', data[2:6])[0]
            if file_size != len(data):
                print(f"Предупреждение BMP: размер в заголовке ({file_size}) не совпадает с фактическим ({len(data)})")
            
            # Проверка смещения к данным
            data_offset = struct.unpack('<I', data[10:14])[0]
            if data_offset >= len(data):
                return False
                
            # Проверка размера заголовка
            header_size = struct.unpack('<I', data[14:18])[0]
            if header_size not in [12, 40, 108, 124]:  # BITMAPCOREHEADER, BITMAPINFOHEADER, BITMAPV4HEADER, BITMAPV5HEADER
                print(f"Предупреждение BMP: нестандартный размер заголовка ({header_size})")
            
            return True
        except:
            return False


def menu():
    print("АРХИВАТОР LZ*")
    print("=" * 50)
    print("1. Сжать файл")
    print("2. Распаковать файл")
    print("0. Выход")

def get_window_size_recommendation(file_extension: str, file_size: int) -> int:
    
    # Базовые рекомендации по типам файлов
    base_recommendations = {
        # Текстовые файлы - большие окна для поиска повторений
        'txt': 8192,
        'log': 16384,  # Логи часто имеют повторяющиеся паттерны
        'csv': 12288,
        'xml': 10240,
        'json': 10240,
        'html': 12288,
        
        # Исходный код
        'py': 8192,
        'cpp': 8192,
        'c': 8192,
        'java': 8192,
        'js': 8192,
        
        # Графические файлы
        'bmp': 4096,   # BMP имеет структурированные данные
        'tiff': 6144,
        
        # Уже сжатые форматы - маленькие окна
        'jpg': 1024,
        'jpeg': 1024,
        'png': 1024,
        'gif': 1024,
        'zip': 512,
        'rar': 512,
        '7z': 512,
        
        # Исполняемые файлы
        'exe': 6144,
        'dll': 6144,
        'bin': 4096,
        
        # Прочие
        'pdf': 2048,
        'doc': 3072,
        'docx': 2048,
    }
    
    base_size = base_recommendations.get(file_extension.lower(), 4096)
    
    # Адаптация по размеру файла
    if file_size < 1024:  # < 1KB
        return min(256, max(64, file_size * 2))
    elif file_size < 10240:  # < 10KB
        return min(base_size, max(512, file_size // 2))
    elif file_size < 102400:  # < 100KB
        return min(base_size * 2, max(1024, file_size // 4))
    elif file_size < 1048576:  # < 1MB
        return min(base_size * 4, max(2048, file_size // 8))
    else:  # >= 1MB
        return min(65535, max(4096, base_size * 4))


def show_window_recommendations(file_extension: str, file_size: int):
    recommended = get_window_size_recommendation(file_extension, file_size)
    print(f"Анализ файла: .{file_extension}, {file_size} байт")
    print(f"Рекомендуемый размер окна: {recommended} байт")
    print("=" * 50)


def main():
    archiver = LZStarArchiver()
    print("Лабораторная работа №5: Архиватор LZ")
    while True:
        menu()
        try:
            choice = input("Выберите действие (0-3): ").strip()
            
            if choice == '1':
                input_file = input("Введите путь к файлу для сжатия: ").strip()
                
                if not os.path.exists(input_file):
                    print("Ошибка: файл не существует!")
                    continue
                
                file_ext = os.path.splitext(input_file)[1]
                if file_ext:
                    file_ext = file_ext[1:]  # Убираем точку
                else:
                    file_ext = "unknown"
                    
                file_size = os.path.getsize(input_file)
                
                show_window_recommendations(file_ext, file_size)
                
                output_file = input("Введите путь для сжатого файла: ").strip()
                if not output_file:
                    output_file = input_file + '.lz'
                
                recommended_size = get_window_size_recommendation(file_ext, file_size)
                window_input = input(f"Введите размер окна [{recommended_size}]: ").strip()
                
                try:
                    window_size = int(window_input) if window_input else recommended_size
                except ValueError:
                    print("Неверный формат! Используется рекомендуемое значение.")
                    window_size = recommended_size
                
                if window_size < 1:
                    print("Размер окна должен быть положительным! Установлено рекомендуемое значение.")
                    window_size = recommended_size
                elif window_size > 65535:
                    print("Максимальный размер окна - 65535! Установлено 65535.")
                    window_size = 65535
                
                print(f"Используется размер окна: {window_size} байт")
                
                archiver.compress(input_file, output_file, window_size)
                
            elif choice == '2':
                input_file = input("Введите путь к сжатому файлу: ").strip()
                
                if not os.path.exists(input_file):
                    print("Ошибка: файл не существует!")
                    continue
                
                output_file = input("Введите путь для распакованного файла: ").strip()
                if not output_file:
                    # Улучшенная логика для распаковки - сохраняем оригинальное расширение
                    if input_file.endswith('.lz'):
                        base_name = input_file[:-3]  # Убираем .lz
                        # Восстанавливаем оригинальное имя файла
                        output_file = base_name
                    else:
                        output_file = input_file + '_decompressed'
                
                archiver.decompress(input_file, output_file)
                
            elif choice == '0':
                print("Выход из программы.")
                break
            else:
                print("Неверный выбор! Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n\nВыход из программы.")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()