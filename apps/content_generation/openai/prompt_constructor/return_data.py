# apps/content_generation/openai/prompt_constructor/return_data.py
from decimal import Decimal

from apps.selection.models import (
    SelectionTaskType,
)

# В функцию get_prompts приходит data_collection следующего вида

data_collection = {
    'article_ga': '19000002015',
    'image_key': None,
    'ingredients_list': ['Water',
                         'Dimethicone',
                         'Butylene Glycol',
                         'Glycerin',
                         'Trisiloxane',
                         'Trehalose',
                         'Sucrose',
                         'Ammonium Acryloyldimethyltaurate/vp Copolymer',
                         'Hydroxyethyl Urea',
                         'Camellia Sinensis (green Tea) Leaf Extract',
                         "Silybum Marianum (lady's Thistle) Extract",
                         'Betula Alba (birch) Bark Extract',
                         'Saccharomyces Lysate Extract',
                         'Aloe Barbadensis Leaf Water',
                         'Aloe Barbadensis Leaf Extract',
                         'Thermus Thermophillus Ferment',
                         'Caffeine',
                         'Sorbitol',
                         'Palmitoyl Hexapeptide-12',
                         'Sodium Hyaluronate',
                         'Caprylyl Glycol',
                         'Oleth-10',
                         'Sodium Polyaspartate',
                         'Aloe Barbadensis Leaf Polysaccharides',
                         'Lactobacillus Ferment Lysate',
                         'Saccharide Isomerate',
                         'Hydrogenated Lecithin',
                         'Tocopheryl Acetate',
                         'Acrylates/c10-30 Alkyl Acrylate Crosspolymer',
                         'Glyceryl Polymethacrylate',
                         'Tromethamine',
                         'PEG-8',
                         'Hexylene Glycol',
                         'Magnesium Ascorbyl Phosphate',
                         'Citric Acid',
                         'BHT',
                         'Disodium EDTA',
                         'Sodium Citrate',
                         'Potassium Sorbate',
                         'Sodium Benzoate',
                         'Phenoxyethanol',
                         'Red 4 (ci 14700)',
                         'Yellow 5 (ci 19140)'],
    'measure_unit': 'мл',
    'measure_value': Decimal('15.00'),
    'name': 'CLINIQUE Moisture Surge 100h',
    'price_rub': Decimal('2100.00'),
    'product_type': 'гель для лица',
    'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
    'Номер шага задачи': 1,
    'Смещение для нумерации': 1,
    'Шаг задачи последний или нет': False,
    'Элементы состава для шага задачи': ['Water',
                                         'Dimethicone',
                                         'Butylene Glycol',
                                         'Glycerin',
                                         'Trisiloxane',
                                         'Trehalose',
                                         'Sucrose',
                                         'Ammonium Acryloyldimethyltaurate/vp '
                                         'Copolymer',
                                         'Hydroxyethyl Urea',
                                         'Camellia Sinensis (green Tea) Leaf '
                                         'Extract'],
}

# Затем словарь расшифровывается и модифицируется
result_decrypted_data = {
    'ingredients_list': [],
    'article_ga': '19000002015',
    'decryption_task': 'Тебе дано средство и часть элементов его состава. Тебе '
                       'надо разобрать каждый элемент состава средства. '
                       'Внимательно изучаешь и выдаёшь результат в соответствии с '
                       'json схемой. Ответы должны быть понятны человеку без '
                       'медицинского образования, старайся отвечать понятно, без '
                       'сложных формулировок. Отвечай всегда на русском языке.',
    'name': 'CLINIQUE Moisture Surge 100h',
    'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
    'specialist': 'Ты высококвалифицированный врач. Твоя задача подобрать '
                  'максимально подходящее средство для человека. Данные человека '
                  'будут даны.',
    'task_type': SelectionTaskType.COMPOSITION_ANALYSIS,
    'Номер шага задачи': 1,
    'Шаг задачи последний или нет': False,
    'Элементы состава для шага задачи': '1_Water, 2_Dimethicone, 3_Butylene '
                                        'Glycol, 4_Glycerin, 5_Trisiloxane, '
                                        '6_Trehalose, 7_Sucrose, 8_Ammonium '
                                        'Acryloyldimethyltaurate/vp Copolymer, '
                                        '9_Hydroxyethyl Urea, 10_Camellia '
                                        'Sinensis (green Tea) Leaf Extract',
}
