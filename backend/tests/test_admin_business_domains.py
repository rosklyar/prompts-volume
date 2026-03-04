"""Tests for admin business domain CRUD endpoints."""

from src.keyword_inspiration.domain_prompts import FALLBACK_TEMPLATE


VALID_TEMPLATE = """\
You are an expert for {domain_name}.
Keywords: {keywords} ({keywords_count} total).
Language: {language}.
Return JSON: {{{{"prompts": [...]}}}}"""

INVALID_TEMPLATE = "Hello {unknown_placeholder}"


class TestListBusinessDomainsAdmin:
    """Tests for GET /admin/api/v1/business-domains."""

    def test_requires_superuser(self, client, auth_headers):
        response = client.get("/admin/api/v1/business-domains", headers=auth_headers)
        assert response.status_code == 403

    def test_list_includes_inactive(self, client, superuser_auth_headers):
        # Create a domain then soft-delete it
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "inactive-domain",
                "description": "Will be deactivated",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        assert create_resp.status_code == 201
        domain_id = create_resp.json()["id"]

        # Soft-delete
        del_resp = client.delete(
            f"/admin/api/v1/business-domains/{domain_id}",
            headers=superuser_auth_headers,
        )
        assert del_resp.status_code == 204

        # Admin list should include inactive domain
        list_resp = client.get(
            "/admin/api/v1/business-domains",
            headers=superuser_auth_headers,
        )
        assert list_resp.status_code == 200
        names = [d["name"] for d in list_resp.json()["business_domains"]]
        assert "inactive-domain" in names

        # Verify it's marked inactive
        domain = next(d for d in list_resp.json()["business_domains"] if d["name"] == "inactive-domain")
        assert domain["is_active"] is False


class TestGetDefaultTemplate:
    """Tests for GET /admin/api/v1/business-domains/default-template."""

    def test_returns_fallback_template(self, client, superuser_auth_headers):
        response = client.get(
            "/admin/api/v1/business-domains/default-template",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["template"] == FALLBACK_TEMPLATE


class TestCreateBusinessDomain:
    """Tests for POST /admin/api/v1/business-domains."""

    def test_create_happy_path(self, client, superuser_auth_headers):
        response = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "test-domain",
                "description": "A test domain",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-domain"
        assert data["description"] == "A test domain"
        assert data["system_prompt_template"] == VALID_TEMPLATE
        assert data["is_active"] is True

    def test_create_duplicate_name_409(self, client, superuser_auth_headers):
        payload = {
            "name": "dup-domain",
            "description": "First",
            "system_prompt_template": VALID_TEMPLATE,
        }
        resp1 = client.post(
            "/admin/api/v1/business-domains",
            json=payload,
            headers=superuser_auth_headers,
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/admin/api/v1/business-domains",
            json=payload,
            headers=superuser_auth_headers,
        )
        assert resp2.status_code == 409

    def test_create_invalid_template_422(self, client, superuser_auth_headers):
        response = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "bad-template-domain",
                "description": "Has bad template",
                "system_prompt_template": INVALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        assert response.status_code == 422


class TestUpdateBusinessDomain:
    """Tests for PATCH /admin/api/v1/business-domains/{domain_id}."""

    def test_update_description_only(self, client, superuser_auth_headers):
        # Create domain first
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "update-desc-domain",
                "description": "Original",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        update_resp = client.patch(
            f"/admin/api/v1/business-domains/{domain_id}",
            json={"description": "Updated description"},
            headers=superuser_auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["description"] == "Updated description"
        # Template should be unchanged
        assert update_resp.json()["system_prompt_template"] == VALID_TEMPLATE

    def test_update_template_with_validation(self, client, superuser_auth_headers):
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "update-tpl-domain",
                "description": "For template update",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        new_template = "New template for {domain_name} with {keywords} in {language}. Count: {keywords_count}. JSON: {{{{}}}}"
        update_resp = client.patch(
            f"/admin/api/v1/business-domains/{domain_id}",
            json={"system_prompt_template": new_template},
            headers=superuser_auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["system_prompt_template"] == new_template

    def test_update_invalid_template_422(self, client, superuser_auth_headers):
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "update-bad-tpl",
                "description": "For bad template update",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        update_resp = client.patch(
            f"/admin/api/v1/business-domains/{domain_id}",
            json={"system_prompt_template": INVALID_TEMPLATE},
            headers=superuser_auth_headers,
        )
        assert update_resp.status_code == 422

    def test_update_nonexistent_404(self, client, superuser_auth_headers):
        response = client.patch(
            "/admin/api/v1/business-domains/999999",
            json={"description": "Does not exist"},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404

    def test_update_empty_body_422(self, client, superuser_auth_headers):
        """Providing neither description nor template should fail validation."""
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "update-empty-body",
                "description": "For empty body test",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        response = client.patch(
            f"/admin/api/v1/business-domains/{domain_id}",
            json={},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 422


class TestDeleteBusinessDomain:
    """Tests for DELETE /admin/api/v1/business-domains/{domain_id}."""

    def test_soft_delete_happy_path(self, client, superuser_auth_headers):
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "delete-domain",
                "description": "Will be deleted",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/admin/api/v1/business-domains/{domain_id}",
            headers=superuser_auth_headers,
        )
        assert del_resp.status_code == 204

    def test_delete_nonexistent_404(self, client, superuser_auth_headers):
        response = client.delete(
            "/admin/api/v1/business-domains/999999",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404


class TestReferenceListExcludesInactive:
    """Reference endpoint should exclude inactive domains."""

    def test_reference_excludes_inactive(self, client, superuser_auth_headers, auth_headers):
        # Create and soft-delete a domain
        create_resp = client.post(
            "/admin/api/v1/business-domains",
            json={
                "name": "ref-inactive-domain",
                "description": "Will be deactivated",
                "system_prompt_template": VALID_TEMPLATE,
            },
            headers=superuser_auth_headers,
        )
        domain_id = create_resp.json()["id"]

        client.delete(
            f"/admin/api/v1/business-domains/{domain_id}",
            headers=superuser_auth_headers,
        )

        # Reference list (regular user) should NOT include inactive
        ref_resp = client.get(
            "/api/v1/reference/business-domains",
            headers=auth_headers,
        )
        assert ref_resp.status_code == 200
        names = [d["name"] for d in ref_resp.json()["business_domains"]]
        assert "ref-inactive-domain" not in names
