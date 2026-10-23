from django.test import TestCase


class ApiDocsTests(TestCase):
    def test_schema_endpoint_serves_openapi(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("/api/recipes/", content)
        self.assertIn("jwtAuth", content)

    def test_schema_documents_nested_actions(self):
        content = self.client.get("/api/schema/").content.decode()
        self.assertIn("recipe-ingredients", content)
        self.assertIn("/api/plans/", content)
        self.assertIn("meal_type", content)

    def test_swagger_ui_renders(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)

    def test_redoc_renders(self):
        response = self.client.get("/api/redoc/")
        self.assertEqual(response.status_code, 200)
