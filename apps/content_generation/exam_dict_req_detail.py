# apps/content_generation/exam_dict_req_detail.py
# такая структура приходит в get_access_key

request_details = {
    "service": "openai",
    "model": "gpt-4o-mini",
    "target": "text",
    "json_scheme": {},
    "context": [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "Ты профессиональный эксперт по косметике с мед.образованием.",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Напиши о том, как правильно ухаживать за собой женщине в 31 год",
                }
            ],
        },
    ],
    "pictures": None,
}
