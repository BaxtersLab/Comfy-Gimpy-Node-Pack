"""
Tests for shared/protocol.py
"""

import unittest
import json
import base64
from shared.protocol import PingResponse, WorkflowRequest, WorkflowResponse, encode_params, decode_base64_image, validate_workflow_request, validate_workflow_response

class TestProtocol(unittest.TestCase):
    def test_ping_response(self):
        resp = PingResponse(status="ok", comfyui_version="1.0", models_available=["model1"])
        self.assertEqual(resp.status, "ok")

    def test_encode_decode_params(self):
        params = {"key": "value"}
        encoded = encode_params(params)
        self.assertEqual(encoded, '{"key": "value"}')

    def test_base64_image(self):
        data = b"test data"
        encoded = base64.b64encode(data).decode()
        decoded = decode_base64_image(encoded)
        self.assertEqual(decoded, data)

    def test_validate_workflow_request_valid(self):
        req = WorkflowRequest(mode="inpaint", workflow_name="test", params={})
        validate_workflow_request(req)  # Should not raise

    def test_validate_workflow_request_invalid(self):
        req = WorkflowRequest(mode="", workflow_name="", params={})
        with self.assertRaises(ValueError):
            validate_workflow_request(req)

    def test_validate_workflow_response_valid(self):
        resp = WorkflowResponse(status="completed", task_id="123", result={})
        validate_workflow_response(resp)  # Should not raise

    def test_validate_workflow_response_invalid(self):
        resp = WorkflowResponse(status="invalid", task_id="", result={})
        with self.assertRaises(ValueError):
            validate_workflow_response(resp)

if __name__ == '__main__':
    unittest.main()