"""
ForgePilot API Tests
Tests for: Projects CRUD, Ollama status, GitHub endpoints, Files, Agents
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndRoot:
    """Root endpoint and health check tests"""
    
    def test_root_endpoint(self):
        """Test GET /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "ForgePilot API"
        assert "version" in data
        assert "ollama" in data
        print(f"✓ Root endpoint working: {data}")

class TestOllamaStatus:
    """Ollama status endpoint tests"""
    
    def test_ollama_status_endpoint(self):
        """Test GET /api/ollama/status returns status"""
        response = requests.get(f"{BASE_URL}/api/ollama/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "models" in data
        assert isinstance(data["available"], bool)
        assert isinstance(data["models"], list)
        print(f"✓ Ollama status endpoint working: available={data['available']}, models={data['models']}")

class TestProjectsCRUD:
    """Projects CRUD operations tests"""
    
    def test_get_projects_list(self):
        """Test GET /api/projects returns list of projects"""
        response = requests.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/projects returned {len(data)} projects")
        
        # Verify project structure if projects exist
        if len(data) > 0:
            project = data[0]
            assert "id" in project
            assert "name" in project
            assert "project_type" in project
            assert "status" in project
            print(f"✓ Project structure verified: {project['name']}")
    
    def test_create_project(self):
        """Test POST /api/projects creates a new project"""
        test_name = f"TEST_Project_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "description": "Test project created by automated tests",
            "project_type": "fullstack"
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Verify created project
        assert data["name"] == test_name
        assert data["description"] == payload["description"]
        assert data["project_type"] == "fullstack"
        assert "id" in data
        assert "created_at" in data
        assert "workspace_path" in data
        print(f"✓ Project created: {data['id']}")
        
        # Verify project exists via GET
        get_response = requests.get(f"{BASE_URL}/api/projects/{data['id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["name"] == test_name
        print(f"✓ Project verified via GET: {fetched['name']}")
        
        # Cleanup - delete the test project
        delete_response = requests.delete(f"{BASE_URL}/api/projects/{data['id']}")
        assert delete_response.status_code == 200
        print(f"✓ Test project deleted: {data['id']}")
    
    def test_get_single_project(self):
        """Test GET /api/projects/{id} returns single project"""
        # First get list to find an existing project
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == project_id
            print(f"✓ GET single project working: {data['name']}")
        else:
            pytest.skip("No projects available to test")
    
    def test_get_nonexistent_project(self):
        """Test GET /api/projects/{id} returns 404 for non-existent project"""
        fake_id = "nonexistent-project-id-12345"
        response = requests.get(f"{BASE_URL}/api/projects/{fake_id}")
        assert response.status_code == 404
        print("✓ 404 returned for non-existent project")

class TestProjectAgents:
    """Project agents endpoint tests"""
    
    def test_get_project_agents(self):
        """Test GET /api/projects/{id}/agents returns 7 agents"""
        # Get an existing project
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/agents")
            assert response.status_code == 200
            agents = response.json()
            
            # Should have 7 agents
            assert isinstance(agents, list)
            assert len(agents) == 7
            
            # Verify all agent types are present
            agent_types = [a["agent_type"] for a in agents]
            expected_types = ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]
            for expected in expected_types:
                assert expected in agent_types, f"Missing agent type: {expected}"
            
            print(f"✓ All 7 agents present: {agent_types}")
        else:
            pytest.skip("No projects available to test")

class TestProjectFiles:
    """Project files endpoint tests"""
    
    def test_get_project_files(self):
        """Test GET /api/projects/{id}/files returns file tree"""
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/files")
            assert response.status_code == 200
            data = response.json()
            
            assert "type" in data
            assert "tree" in data
            print(f"✓ Files endpoint working, type: {data['type']}, tree items: {len(data.get('tree', []))}")
        else:
            pytest.skip("No projects available to test")

class TestProjectMessages:
    """Project messages endpoint tests"""
    
    def test_get_project_messages(self):
        """Test GET /api/projects/{id}/messages returns messages"""
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/messages")
            assert response.status_code == 200
            messages = response.json()
            
            assert isinstance(messages, list)
            print(f"✓ Messages endpoint working, count: {len(messages)}")
        else:
            pytest.skip("No projects available to test")

class TestProjectRoadmap:
    """Project roadmap endpoint tests"""
    
    def test_get_project_roadmap(self):
        """Test GET /api/projects/{id}/roadmap returns roadmap items"""
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/roadmap")
            assert response.status_code == 200
            roadmap = response.json()
            
            assert isinstance(roadmap, list)
            print(f"✓ Roadmap endpoint working, items: {len(roadmap)}")
        else:
            pytest.skip("No projects available to test")

class TestProjectLogs:
    """Project logs endpoint tests"""
    
    def test_get_project_logs(self):
        """Test GET /api/projects/{id}/logs returns logs"""
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/logs")
            assert response.status_code == 200
            logs = response.json()
            
            assert isinstance(logs, list)
            print(f"✓ Logs endpoint working, count: {len(logs)}")
        else:
            pytest.skip("No projects available to test")

class TestProjectPreview:
    """Project preview endpoint tests"""
    
    def test_get_preview_info(self):
        """Test GET /api/projects/{id}/preview-info returns preview info"""
        list_response = requests.get(f"{BASE_URL}/api/projects")
        projects = list_response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}/preview-info")
            assert response.status_code == 200
            data = response.json()
            
            assert "has_preview" in data
            assert "entry_point" in data
            assert "preview_url" in data
            assert "ready_for_push" in data
            print(f"✓ Preview info endpoint working: has_preview={data['has_preview']}")
        else:
            pytest.skip("No projects available to test")

class TestProjectTypes:
    """Test different project types"""
    
    def test_create_fullstack_project(self):
        """Test creating fullstack project type"""
        test_name = f"TEST_Fullstack_{uuid.uuid4().hex[:8]}"
        payload = {"name": test_name, "description": "Test", "project_type": "fullstack"}
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["project_type"] == "fullstack"
        print(f"✓ Fullstack project created")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{data['id']}")
    
    def test_create_mobile_project(self):
        """Test creating mobile project type"""
        test_name = f"TEST_Mobile_{uuid.uuid4().hex[:8]}"
        payload = {"name": test_name, "description": "Test", "project_type": "mobile"}
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["project_type"] == "mobile"
        print(f"✓ Mobile project created")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{data['id']}")
    
    def test_create_landing_project(self):
        """Test creating landing page project type"""
        test_name = f"TEST_Landing_{uuid.uuid4().hex[:8]}"
        payload = {"name": test_name, "description": "Test", "project_type": "landing"}
        response = requests.post(f"{BASE_URL}/api/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["project_type"] == "landing"
        print(f"✓ Landing page project created")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{data['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
