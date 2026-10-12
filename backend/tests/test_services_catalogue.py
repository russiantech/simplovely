import io

from tests.conftest import login
from web.apis.models.services import Area, Service


def req_body(**kw):
    area, service = Area.query.first(), Service.query.first()
    return {"name": "Ada", "phone": "08012345678", "email": "ada@example.com", "quantity": 3, "address": "12 Lekki", "area_id": area.id, "service_id": service.id, **kw}


def test_public_catalogue_and_validated_requests(client, alice, admin):
    assert len(client.get("/api/areas").get_json()["areas"]) >= 5
    assert client.get("/api/service-categories").status_code == 200  # used to 500
    assert client.get("/api/services").status_code == 200
    r = client.post("/api/service-requests", json=req_body())
    assert r.status_code == 201 and r.get_json()["area_name"]
    for bad in ({"quantity": 0}, {"quantity": "x"}, {"phone": "abc"}, {"email": "no"}, {"area_id": 9999}, {"name": ""}):
        assert client.post("/api/service-requests", json=req_body(**bad)).status_code == 400, bad
    assert client.get("/api/service-requests").status_code == 401  # no public PII
    ha, hadmin = login(client, alice), login(client, admin)
    assert client.get("/api/service-requests", headers=ha).get_json()["service_requests"] == []
    rid = client.get("/api/service-requests", headers=hadmin).get_json()["service_requests"][0]["id"]
    assert client.put(f"/api/service-requests/{rid}", json={"status": "Confirmed"}, headers=hadmin).get_json()["status"] == "Confirmed"  # used to crash
    assert client.put(f"/api/service-requests/{rid}", json={"status": "???"}, headers=hadmin).status_code == 400
    assert client.delete(f"/api/service-requests/{rid}", headers=hadmin).status_code == 200  # used to 500 after deleting
    assert client.delete(f"/api/service-requests/{rid}", headers=hadmin).status_code == 404


def test_old_public_mutation_endpoints_are_gone(client):
    for path in ("/api/insert-areas", "/api/insert-services", "/api/populate"):
        assert client.get(path).status_code == 404


def test_catalogue_writes_require_admin(client, alice, admin):
    ha, hadmin = login(client, alice), login(client, admin)
    assert client.post("/api/categories", json={"name": "Hack"}).status_code == 401
    assert client.post("/api/categories", json={"name": "Hack"}, headers=ha).status_code == 403
    assert client.post("/api/products", data={"name": "Hack", "price": "1"}, headers=ha).status_code == 403
    assert client.delete("/api/categories/1", headers=ha).status_code == 403
    assert client.post("/api/countries", json={"name": "Nowhere", "code": "NW"}, headers=ha).status_code == 403


def test_product_lifecycle_pagination_slugs(client, admin):
    h = {**login(client, admin)}
    cat = client.post("/api/categories", json={"name": "Ankara", "description": "Prints"}, headers=h)
    assert cat.status_code == 201 and client.post("/api/categories", json={"name": "ankara"}, headers=h).status_code == 409
    for i in range(1, 5):
        form = {"name": f"{i}-piece set", "price": str(1000 * i), "stock": "3", "description": "d", "categories[0][name]": "Ankara"}
        r = client.post("/api/products", data={**form, "images[]": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 20), "a.png")}, headers=h, content_type="multipart/form-data")
        assert r.status_code == 201, r.get_json()
    page1 = client.get("/api/products?page_size=3").get_json()
    page2 = client.get("/api/products?page_size=3&page=2").get_json()
    assert len(page1["products"]) == 3 and len(page2["products"]) == 1  # pagination was ignored (cached)
    assert client.get(f"/api/products?category_id={cat.get_json()['id']}").get_json()["page_meta"]["total_items_count"] == 4
    by_slug = client.get("/api/products/2-piece-set/slug").get_json()
    assert by_slug["name"] == "2-piece set" and by_slug["description"] == "d"
    assert client.get("/api/products/ankara/category").get_json()["page_meta"]["total_items_count"] == 4
    # deleting by slug removes exactly that product (a digit-leading slug used to hit id 2)
    assert client.delete("/api/products/2-piece-set", headers=h).status_code == 200
    names = [p["name"] for p in client.get("/api/products").get_json()["products"]]
    assert "2-piece set" not in names and len(names) == 3
    pid = client.get("/api/products").get_json()["products"][0]["id"]
    r = client.put(f"/api/products/{pid}", data={"price": "777"}, headers=h, content_type="multipart/form-data")
    assert r.get_json()["price"] == 777 and r.get_json()["stock"] == 3  # stock no longer reset to 0
    assert client.put("/api/products/9999", data={"price": "1"}, headers=h).status_code == 404


def test_exclude_and_default_category_page_size(client, admin):
    h = login(client, admin)
    for i in range(12):
        client.post("/api/categories", json={"name": f"Cat {i}"}, headers=h)
    assert len(client.get("/api/categories").get_json()["categories"]) == 12  # public page shows all tabs
    ids = []
    for n in ("A", "B", "C"):
        ids.append(client.post("/api/products", data={"name": n, "price": "1"}, headers=h).get_json()["id"])
    res = client.get(f"/api/products?exclude={ids[0]}").get_json()["products"]
    assert ids[0] not in [p["id"] for p in res] and len(res) == 2
