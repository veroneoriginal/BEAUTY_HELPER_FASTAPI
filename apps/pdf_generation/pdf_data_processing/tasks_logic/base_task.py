# apps/pdf_generation/pdf_data_processing/tasks_logic/base_task.py

from apps.pdf_generation.utils import (
    calc_base_price_ratio,
    capitalize_first_letter,
    extract_product_name,
)


def get_base_info_by_product(
    product_data: dict,
) -> dict:
    """
    Получает базовые данные по средству.

    :param product_data: DTO средства
    :return: данные по средству для титульного листа
    """

    return {
        # одинаково для всех средств:
        "Название средства": extract_product_name(product_data["name"]),
        "Количество мера / цена": calc_base_price_ratio(product_data),
        "Путь к изображению средства": product_data["image_key"],
        "Тип продукта": capitalize_first_letter(
            product_data["product_type"] or product_data["product_type_detailed"]
        ),
        "Артикул": f"артикул: {product_data['article_ga']}",
    }
