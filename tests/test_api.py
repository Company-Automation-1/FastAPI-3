import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.models.task import TaskStatus
from tests.conftest import TestDevice, TestTask, TestUpload

# 模拟API测试，不实际调用API

class TestDeviceAPI:
    """测试设备API"""
    
    def test_device_endpoints_exist(self, client):
        """测试设备API端点是否存在"""
        # 为测试准备单独的测试文件
        # 仅验证API结构而不是实际功能
        
        # 测试路由存在
        available_routes = [route.path for route in client.app.routes]
        assert "/api/v1/devices/" in available_routes


class TestTaskAPI:
    """测试任务API"""
    
    def test_task_endpoints_exist(self, client):
        """测试任务API端点是否存在"""
        # 为测试准备单独的测试文件
        # 仅验证API结构而不是实际功能
        
        # 测试路由存在
        available_routes = [route.path for route in client.app.routes]
        assert "/api/v1/tasks/" in available_routes

    def test_get_devices(self, client, sample_device):
        """测试获取设备列表"""
        response = client.get("/api/v1/devices/")
        
        # 验证状态码和返回格式
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # 验证返回的设备数据
        devices = response.json()
        assert len(devices) >= 1
        assert any(d["device_name"] == sample_device.device_name for d in devices)
    
    def test_get_device_by_name(self, client, sample_device):
        """测试通过名称获取设备"""
        response = client.get(f"/api/v1/devices/{sample_device.device_name}")
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        device_data = response.json()
        assert device_data["device_name"] == sample_device.device_name
        assert device_data["device_id"] == sample_device.device_id
    
    def test_create_device(self, client):
        """测试创建设备"""
        # 准备测试数据
        new_device = {
            "device_id": "new_test_id",
            "device_name": "new_test_device",
            "device_path": "/storage/test/",
            "password": "0000"
        }
        
        # 发送创建请求
        response = client.post("/api/v1/devices/", json=new_device)
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        device_data = response.json()
        assert device_data["device_name"] == new_device["device_name"]
        assert device_data["device_id"] == new_device["device_id"]
    
    def test_update_device(self, client, sample_device):
        """测试更新设备"""
        # 准备更新数据
        update_data = {
            "device_path": "/storage/updated/",
            "password": "9999"
        }
        
        # 发送更新请求
        response = client.put(f"/api/v1/devices/{sample_device.device_name}", json=update_data)
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        device_data = response.json()
        assert device_data["device_path"] == update_data["device_path"]
        assert device_data["password"] == update_data["password"]
        
    def test_delete_device(self, client):
        """测试删除设备"""
        # 先创建要删除的设备
        new_device = {
            "device_id": "device_to_delete",
            "device_name": "delete_test",
            "device_path": "/storage/test/",
            "password": "0000"
        }
        client.post("/api/v1/devices/", json=new_device)
        
        # 发送删除请求
        response = client.delete(f"/api/v1/devices/{new_device['device_name']}")
        
        # 验证状态码
        assert response.status_code == 200
        
        # 验证设备已删除
        get_response = client.get(f"/api/v1/devices/{new_device['device_name']}")
        assert get_response.status_code == 404

    def test_get_tasks(self, client, sample_task):
        """测试获取任务列表"""
        response = client.get("/api/v1/tasks/")
        
        # 验证状态码和返回格式
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # 验证返回的任务数据
        tasks = response.json()
        assert len(tasks) >= 1
        assert any(t["id"] == sample_task.id for t in tasks)
    
    def test_get_task_by_id(self, client, sample_task):
        """测试通过ID获取任务"""
        response = client.get(f"/api/v1/tasks/{sample_task.id}")
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["id"] == sample_task.id
        assert task_data["device_name"] == sample_task.device_name
    
    def test_create_task(self, client, sample_device, sample_upload):
        """测试创建任务"""
        # 准备测试数据
        new_task = {
            "device_name": sample_device.device_name,
            "upload_id": sample_upload.id,
            "status": TaskStatus.WT,
            "time": 1623456790
        }
        
        # 发送创建请求
        response = client.post("/api/v1/tasks/", json=new_task)
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["device_name"] == new_task["device_name"]
        assert task_data["upload_id"] == new_task["upload_id"]
        assert task_data["status"] == new_task["status"]
    
    def test_update_task_status(self, client, sample_task):
        """测试更新任务状态"""
        # 准备更新数据
        update_data = {
            "status": TaskStatus.PENDING
        }
        
        # 发送更新请求
        response = client.put(f"/api/v1/tasks/{sample_task.id}/status", json=update_data)
        
        # 验证状态码和返回数据
        assert response.status_code == 200
        task_data = response.json()
        assert task_data["status"] == update_data["status"]
        
    def test_delete_task(self, client, sample_device, sample_upload):
        """测试删除任务"""
        # 先创建要删除的任务
        new_task = {
            "device_name": sample_device.device_name,
            "upload_id": sample_upload.id,
            "status": TaskStatus.WT,
            "time": 1623456790
        }
        create_response = client.post("/api/v1/tasks/", json=new_task)
        task_id = create_response.json()["id"]
        
        # 发送删除请求
        response = client.delete(f"/api/v1/tasks/{task_id}")
        
        # 验证状态码
        assert response.status_code == 200
        
        # 验证任务已删除
        get_response = client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 404 