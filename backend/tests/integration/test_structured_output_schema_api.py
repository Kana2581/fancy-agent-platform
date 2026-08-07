async def test_structured_output_schema_crud_is_user_scoped(api_client, create_user_and_login):
    _, owner_headers = await create_user_and_login(
        username="schemaowner",
        email="schemaowner@example.com",
    )
    _, other_headers = await create_user_and_login(
        username="schemaother",
        email="schemaother@example.com",
    )
    payload = {
        "name": "合同字段提取",
        "description": "提取合同核心字段",
        "field_config": {
            "fields": [
                {
                    "key": "contract_no",
                    "label": "合同编号",
                    "type": "string",
                    "description": "合同中明确标注的编号",
                },
                {
                    "key": "currency",
                    "label": "币种",
                    "type": "enum",
                    "enum_values": ["CNY", "USD"],
                },
            ]
        },
    }

    created = await api_client.post(
        "/api/v1/structured-output-schemas",
        json=payload,
        headers=owner_headers,
    )
    assert created.status_code == 200, created.text
    schema_id = created.json()["id"]

    listing = await api_client.get("/api/v1/structured-output-schemas", headers=owner_headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [schema_id]

    for method in ("get", "put", "delete"):
        kwargs = {"json": payload} if method == "put" else {}
        blocked = await getattr(api_client, method)(
            f"/api/v1/structured-output-schemas/{schema_id}",
            headers=other_headers,
            **kwargs,
        )
        assert blocked.status_code == 404

    payload["name"] = "更新后的合同提取"
    updated = await api_client.put(
        f"/api/v1/structured-output-schemas/{schema_id}",
        json=payload,
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "更新后的合同提取"

    deleted = await api_client.delete(
        f"/api/v1/structured-output-schemas/{schema_id}",
        headers=owner_headers,
    )
    assert deleted.status_code == 204


async def test_structured_output_schema_rejects_invalid_fields(api_client, create_user_and_login):
    _, headers = await create_user_and_login(
        username="schemainvalid",
        email="schemainvalid@example.com",
    )
    response = await api_client.post(
        "/api/v1/structured-output-schemas",
        headers=headers,
        json={
            "name": "Invalid",
            "field_config": {
                "fields": [
                    {"key": "duplicate", "label": "A", "type": "string"},
                    {"key": "duplicate", "label": "B", "type": "number"},
                ]
            },
        },
    )
    assert response.status_code == 422
