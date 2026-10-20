from sharp.career import prepare_document


def test_contact_includes_available_city_region_and_country(career, settings, plan):
    career.basics["phone"] = "+1 (206) 555-0147"
    career.basics["location"] = {"city": "Seattle", "region": "Washington", "countryCode": "US"}
    contact = next(b for b in prepare_document(career, settings, plan) if b.id == "contact")
    assert contact.text == "alex@example.com | +1 (206) 555-0147 | Seattle, Washington, US"


def test_partial_location_does_not_add_empty_separators(career, settings, plan):
    career.basics.pop("email")
    career.basics["location"] = {"city": "Seattle"}
    contact = next(b for b in prepare_document(career, settings, plan) if b.id == "contact")
    assert contact.text == "Seattle"
