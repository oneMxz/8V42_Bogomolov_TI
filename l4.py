import heapq
import os
import math
import pickle
import struct
import re
from collections import Counter, defaultdict

# ===========================================================
# Основные алгоритмы эффективного кодирования
# ===========================================================

class Tree:
    def __init__(self, char, probability):
        self.char = char
        self.probability = probability
        self.right = None
        self.left = None
        
    def __lt__(self, other):
        return self.probability < other.probability

def build_huffman_tree(prob_dict):
    nodes = []
    for char, prob in prob_dict.items():
        heapq.heappush(nodes, Tree(char, prob))
    
    while len(nodes) > 1:
        left = heapq.heappop(nodes)
        right = heapq.heappop(nodes)
        
        merged = Tree(None, left.probability + right.probability)
        merged.left = left
        merged.right = right
        
        heapq.heappush(nodes, merged)
    
    return nodes[0] if nodes else None

def generate_huffman_codes(node, prefix="", codebook=None):
    if codebook is None:
        codebook = {}
    
    if node is not None:
        if node.char is not None:
            codebook[node.char] = prefix
        generate_huffman_codes(node.left, prefix + "1", codebook)
        generate_huffman_codes(node.right, prefix + "0", codebook)
    
    return codebook

def min_ras(sortD):
    min_d = float('inf')
    total_prob = sum(prob for _, prob in sortD)
    furst_sum = 0
    index = 0
    for i, (symbol, prob) in enumerate(sortD):
        furst_sum += prob
        diff = abs(2 * furst_sum - total_prob)
        if diff < min_d:
            min_d = diff
            index = i + 1
    
    group1 = dict(sortD[:index])
    group2 = dict(sortD[index:])
    
    return group1, group2
    
def shannon_fano_coding(prob_dict):
    def split_dict(d):
        if len(d) == 1:
            return
        
        sorted_items = sorted(d.items(), key=lambda x: x[1], reverse=True)
        groupA, groupB = min_ras(sorted_items)
        
        for sym in groupA:
            codes[sym] += '1'
        for sym in groupB:
            codes[sym] += '0'
        
        split_dict(groupA)
        split_dict(groupB)
    
    codes = defaultdict(str)
    split_dict(prob_dict)
    return codes


# ==========================================================
# Вспомогательные модули для интеллектуального разбиения на блоки
# ==========================================================

def calculate_entropy(data):
    """Вычисление энтропии данных"""
    if not data:
        return 0
    
    freq = Counter(data)
    total = len(data)
    entropy = 0.0
    
    for count in freq.values():
        probability = count / total
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy

def calculate_redundancy(data):
    """Вычисление избыточности данных по формуле R = 1 - H/Hmax"""
    if not data:
        return 0
    
    H = calculate_entropy(data)
    M = len(Counter(data))
    
    if M <= 1:
        return 0
    
    Hmax = math.log2(M)
    redundancy = 1 - (H / Hmax) if Hmax > 0 else 0
    
    return redundancy

def calculate_algorithm_redundancy(data, codes):
    """Вычисление избыточности для конкретного алгоритма кодирования"""
    if not data or not codes:
        return float('inf')
    
    freq = Counter(data)
    total = len(data)
    avg_code_length = 0
    
    for char, count in freq.items():
        if char in codes:
            probability = count / total
            avg_code_length += probability * len(codes[char])
    
    H = calculate_entropy(data)
    algorithm_redundancy = 1 - (H / avg_code_length) if avg_code_length > 0 else 1
    
    return algorithm_redundancy

def select_best_method(data):
    """Выбор наилучшего метода сжатия на основе избыточности алгоритмов"""
    if not data:
        return 'huffman'
    
    data_redundancy = calculate_redundancy(data)
    print(f"Избыточность данных: {data_redundancy:.4f}")
    
    freq = Counter(data)
    
    # Хаффман
    huffman_tree = build_huffman_tree(freq)
    huffman_codes = generate_huffman_codes(huffman_tree)
    
    # Шеннон-Фано
    prob_dict = {char: count/len(data) for char, count in freq.items()}
    shannon_codes = shannon_fano_coding(prob_dict)
    
    # Вычисляем избыточность для каждого алгоритма
    huffman_redundancy = calculate_algorithm_redundancy(data, huffman_codes)
    shannon_redundancy = calculate_algorithm_redundancy(data, shannon_codes)
    
    print(f"Избыточность алгоритма Хаффмана: {huffman_redundancy:.4f}")
    print(f"Избыточность алгоритма Шеннона-Фано: {shannon_redundancy:.4f}")
    
    if huffman_redundancy <= shannon_redundancy:
        print("Выбран метод Хаффмана (меньшая избыточность алгоритма)")
        return 'huffman'
    else:
        print("Выбран метод Шеннона-Фано (меньшая избыточность алгоритма)")
        return 'shannon_fano'

def find_optimal_block_size(data):
    """Нахождение оптимальной длины блока на основе эффективности кодирования"""
    if len(data) <= 100:
        return len(data)  # Для маленьких файлов - один блок
    
    # Разные кандидаты на длину блока (в словах)
    word_candidates = [1, 2, 3, 5, 8, 13]  # Фибоначчи-подобная последовательность
    
    # Разбиваем текст на слова
    words = re.findall(r'\b\w+\b', data)
    
    if len(words) <= max(word_candidates):
        return len(data)  # Если слов меньше максимального кандидата
    
    best_efficiency = -1
    best_word_count = word_candidates[0]
    
    # Тестируем разные длины блоков (в словах)
    for word_count in word_candidates:
        # Создаем блоки из N слов
        blocks = []
        for i in range(0, len(words), word_count):
            block_words = words[i:i + word_count]
            block = ' '.join(block_words)
            blocks.append(block)
        
        # Оцениваем эффективность сжатия этих блоков
        efficiency = estimate_blocks_efficiency(blocks)
        
        print(f"Длина блока: {word_count} слов, Эффективность: {efficiency:.2f}%")
        
        if efficiency > best_efficiency:
            best_efficiency = efficiency
            best_word_count = word_count
    
    # Преобразуем количество слов в приблизительное количество символов
    avg_word_length = sum(len(word) for word in words) / len(words)
    optimal_char_length = int(best_word_count * avg_word_length + (best_word_count - 1))+1
    
    print(f"Оптимальная длина блока: {best_word_count} слов (~{optimal_char_length} символов)")
    return optimal_char_length

def estimate_blocks_efficiency(blocks):
    """Оценка эффективности сжатия для набора блоков"""
    if not blocks:
        return 0
    
    total_original_size = 0
    total_compressed_size = 0
    
    # Тестируем только первые 5 блоков для скорости
    test_blocks = min(5, len(blocks))
    
    for i in range(test_blocks):
        block = blocks[i]
        original_size = len(block.encode('utf-8'))
        total_original_size += original_size
        
        # Оцениваем сжатый размер (упрощенная оценка)
        freq = Counter(block)
        entropy = calculate_entropy(block)
        estimated_compressed_size = entropy * len(block) / 8  # Байты вместо битов
        total_compressed_size += estimated_compressed_size
    
    if total_original_size == 0:
        return 0
    
    efficiency = (1 - total_compressed_size / total_original_size) * 100
    return max(0, efficiency)

def create_smart_blocks(data, block_size):
    """Создание интеллектуальных блоков на основе оптимальной длины"""
    # Если данные маленькие - один блок
    if len(data) <= block_size:
        return [data]
    
    blocks = []
    current_pos = 0
    
    while current_pos < len(data):
        # Находим конец блока, стараясь не разрывать слова
        end_pos = current_pos + block_size
        
        if end_pos >= len(data):
            # Последний блок
            block = data[current_pos:]
            blocks.append(block)
            break
        
        # Ищем ближайший границу слова (пробел, пунктуация)
        word_boundary = find_word_boundary(data, end_pos)
        
        if word_boundary > current_pos:  # Нашли границу
            block = data[current_pos:word_boundary]
            current_pos = word_boundary
        else:
            # Если не нашли границу, используем фиксированную длину
            block = data[current_pos:end_pos]
            current_pos = end_pos
        
        # Пропускаем пробелы в начале следующего блока
        while current_pos < len(data) and data[current_pos].isspace():
            current_pos += 1
        
        blocks.append(block)
    
    return blocks

def find_word_boundary(text, position):
    """Находит ближайшую границу слова (пробел или пунктуацию)"""
    # Ищем вперед
    for i in range(position, min(position + 50, len(text))):
        if text[i].isspace() or text[i] in ',.!?;:':
            return i + 1  # Включаем разделитель в текущий блок
    
    # Ищем назад
    for i in range(position, max(position - 50, 0), -1):
        if text[i].isspace() or text[i] in ',.!?;:':
            return i + 1
    
    return position  # Не нашли границу

# ==========================================================
# Модули сжатия
# ==========================================================

def bits_to_bytes(bits):
    """Конвертация битовой строки в байты"""
    padding = 8 - len(bits) % 8
    if padding != 8:
        bits += '0' * padding
    
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        byte_array.append(int(byte, 2))
    
    return bytes(byte_array)

def bytes_to_bits(data):
    """Конвертация байтов в битовую строку"""
    bits = ''.join(format(byte, '08b') for byte in data)
    return bits

def huffman_compress(data):
    """Сжатие методом Хаффмана"""
    if not data:
        return b'', {}
    
    freq = Counter(data)
    
    if len(freq) == 1:
        char = list(freq.keys())[0]
        return b'\x00', {char: '0'}
    
    tree = build_huffman_tree(freq)
    codes = generate_huffman_codes(tree)
    
    encoded_bits = ''.join(codes[char] for char in data)
    compressed_bytes = bits_to_bytes(encoded_bits)
    
    return compressed_bytes, codes

def shannon_fano_compress(data):
    """Сжатие методом Шеннона-Фано"""
    if not data:
        return b'', {}
    
    freq = Counter(data)
    prob_dict = {char: count/len(data) for char, count in freq.items()}
    
    codes = shannon_fano_coding(prob_dict)
    encoded_bits = ''.join(codes[char] for char in data)
    compressed_bytes = bits_to_bytes(encoded_bits)
    
    return compressed_bytes, codes

def compress_with_smart_blocks(data):
    """Сжатие с интеллектуальным разбиением на блоки"""
    # Выбираем алгоритм для всего файла
    method = select_best_method(data)
    
    # Находим оптимальную длину блока
    print("Определяем оптимальную длину блока...")
    block_size = find_optimal_block_size(data)
    
    # Создаем интеллектуальные блоки
    blocks = create_smart_blocks(data, block_size)
    
    compressed_blocks = []
    code_tables = []
    
    print(f"Сжимаем {len(blocks)} блоков методом {method}...")
    
    for i, block in enumerate(blocks):
        # Сжимаем блок выбранным методом
        if method == 'huffman':
            compressed_block, codes = huffman_compress(block)
        else:
            compressed_block, codes = shannon_fano_compress(block)
        
        compressed_blocks.append(compressed_block)
        code_tables.append(codes)
        
        if (i + 1) % max(1, len(blocks) // 10) == 0 or (i + 1) == len(blocks):
            print(f"Обработано {i + 1}/{len(blocks)} блоков")
            print(f"  Пример блока: {block[:50]}{'...' if len(block) > 50 else ''}")
    
    # Объединяем блоки
    combined_data = combine_blocks(compressed_blocks)
    
    info = {
        'total_blocks': len(blocks),
        'original_size': len(data),
        'method': method,
        'block_size': block_size
    }
    
    return combined_data, code_tables, info

def combine_blocks(blocks):
    """Объединение блоков с информацией о размерах"""
    result = bytearray()
    result.extend(struct.pack('I', len(blocks)))
    
    for block in blocks:
        result.extend(struct.pack('I', len(block)))
        result.extend(block)
    
    return bytes(result)

def split_blocks(data):
    """Разделение объединенных блоков"""
    blocks = []
    offset = 0
    
    num_blocks = struct.unpack('I', data[offset:offset+4])[0]
    offset += 4
    
    for _ in range(num_blocks):
        block_size = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        block = data[offset:offset+block_size]
        offset += block_size
        blocks.append(block)
    
    return blocks

def huffman_decompress(data, codes):
    """Декомпрессия методом Хаффмана"""
    if not data or not codes:
        return ""
    
    reverse_codes = {v: k for k, v in codes.items()}
    bits = bytes_to_bits(data)
    
    result = []
    current_code = ""
    
    for bit in bits:
        current_code += bit
        if current_code in reverse_codes:
            result.append(reverse_codes[current_code])
            current_code = ""
    
    return ''.join(result)

def shannon_fano_decompress(data, codes):
    """Декомпрессия методом Шеннона-Фано"""
    if not data or not codes:
        return ""
    
    reverse_codes = {v: k for k, v in codes.items()}
    bits = bytes_to_bits(data)
    
    result = []
    current_code = ""
    
    for bit in bits:
        current_code += bit
        if current_code in reverse_codes:
            result.append(reverse_codes[current_code])
            current_code = ""
    
    return ''.join(result)

# ==========================================================
# Функции работы с файлами
# ==========================================================

def resolve_file_path(filename):
    """Разрешение пути к файлу"""
    if os.path.exists(filename):
        return os.path.abspath(filename)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_in_script_dir = os.path.join(script_dir, filename)
    if os.path.exists(file_in_script_dir):
        return file_in_script_dir
    
    cwd = os.getcwd()
    file_in_cwd = os.path.join(cwd, filename)
    if os.path.exists(file_in_cwd):
        return file_in_cwd
    
    return None

def save_compressed_file(filename, compressed_data, codes, info):
    """Сохранение сжатого файла"""
    with open(filename, 'wb') as f:
        f.write(b'ARC1')  # Сигнатура формата
        
        info_data = pickle.dumps(info)
        f.write(struct.pack('I', len(info_data)))
        f.write(info_data)
        
        codes_data = pickle.dumps(codes)
        f.write(struct.pack('I', len(codes_data)))
        f.write(codes_data)
        
        f.write(compressed_data)

def load_compressed_file(filename):
    """Загрузка сжатого файла"""
    with open(filename, 'rb') as f:
        signature = f.read(4)
        if signature != b'ARC1':
            raise ValueError("Неверный формат архива")
        
        info_size = struct.unpack('I', f.read(4))[0]
        info = pickle.loads(f.read(info_size))
        
        codes_size = struct.unpack('I', f.read(4))[0]
        codes = pickle.loads(f.read(codes_size))
        
        compressed_data = f.read()
    
    return info, codes, compressed_data

# ===========================================================
# Основной блок
# ===========================================================

def archiver():
    """Архивация файла с интеллектуальными блоками"""
    filename = input("Введите имя файла для архивации: ").strip()
    
    resolved_path = resolve_file_path(filename)
    if resolved_path is None:
        print("Файл не существует!")
        return
    
    filename = resolved_path
    print(f"Найден файл: {filename}")
    
    # Чтение файла
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
    except UnicodeDecodeError:
        try:
            with open(filename, 'r', encoding='cp1251') as f:
                data = f.read()
        except:
            with open(filename, 'rb') as f:
                data = f.read().decode('latin-1')
    
    if not data:
        print("Файл пуст!")
        return
    
    # Сжимаем с интеллектуальными блоками
    compressed_data, codes, info = compress_with_smart_blocks(data)
    
    # Сохранение архива
    output_filename = filename + '.arc'
    save_compressed_file(output_filename, compressed_data, codes, info)
    
    # Статистика
    original_size = len(data.encode('utf-8') if isinstance(data, str) else len(data))
    compressed_size = len(compressed_data)
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    
    print(f"Архивация завершена!")
    print(f"Использованный метод: {info['method']}")
    print(f"Исходный размер: {original_size} байт")
    print(f"Сжатый размер: {compressed_size} байт")
    print(f"Степень сжатия: {compression_ratio:.2f}%")
    print(f"Количество блоков: {info['total_blocks']}")
    print(f"Оптимальная длина блока: {info['block_size']} символов")
    print(f"Архив сохранен как: {output_filename}")

def unarchiver():
    """Разархивация файла"""
    filename = input("Введите имя архива: ").strip()
    
    resolved_path = resolve_file_path(filename)
    if resolved_path is None:
        print("Архив не существует!")
        return
    
    filename = resolved_path
    
    try:
        # Загрузка архива
        info, codes, compressed_data = load_compressed_file(filename)
        
        # Разделение на блоки
        blocks = split_blocks(compressed_data)
        decompressed_blocks = []
        
        print(f"Разархивируем {len(blocks)} блоков методом {info['method']}...")
        
        # Декомпрессия каждого блока
        for i, block in enumerate(blocks):
            if info['method'] == 'huffman':
                decompressed_block = huffman_decompress(block, codes[i])
            else:
                decompressed_block = shannon_fano_decompress(block, codes[i])
            
            decompressed_blocks.append(decompressed_block)
            
            if (i + 1) % max(1, len(blocks) // 10) == 0 or (i + 1) == len(blocks):
                print(f"Обработано {i + 1}/{len(blocks)} блоков")
        
        # Объединение блоков
        decompressed_data = ''.join(decompressed_blocks)
        
        # Сохранение результата
        if filename.endswith('.arc'):
            output_filename = filename.replace('.arc', '_decompressed.txt')
        else:
            output_filename = filename + '_decompressed.txt'
            
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(decompressed_data)
        
        print(f"Разархивация завершена!")
        print(f"Файл сохранен как: {output_filename}")
        
    except Exception as e:
        print(f"Ошибка при разархивации: {e}")

def main():
    print("Архиватор с интеллектуальным разбиением на блоки\n")
    print("Выберите режим работы:")
    print("1 - архивация файла")
    print("2 - разархивация файла")
    print("0 - выход")
    
    while True:
        choice = input("Ваш выбор: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            archiver()
        elif choice == '2':
            unarchiver()
        else:
            print("Неверный выбор")
        print()

if __name__ == "__main__":
    main()