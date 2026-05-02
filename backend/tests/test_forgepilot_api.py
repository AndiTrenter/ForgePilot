"""
ForgePilot API Tests - Iteration 4
Tests für alle kritischen Backend-Endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-code-master-5.preview.emergentagent.com').rstrip('/')

class TestAPIHealth:
    """API Health und Basis-Tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "ForgePilot API"
        assert "version" in data
        print(f"✓ API Root: {data}")

class TestProjects:
    """Projekt CRUD Tests"""
    
    def test_get_projects(self):
        """Test GET /api/projects"""
        response = requests.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/projects: {len(data)} Projekte gefunden")
    
    def test_get_project_by_id(self):
        """Test GET /api/projects/{id}"""
        # First get list of projects
        response = requests.get(f"{BASE_URL}/api/projects")
        projects = response.json()
        
        if len(projects) > 0:
            project_id = projects[0]["id"]
            response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == project_id
            print(f"✓ GET /api/projects/{project_id}: {data['name']}")
        else:
            pytest.skip("Keine Projekte vorhanden")
    
    def test_get_project_not_found(self):
        """Test GET /api/projects/{id} mit ungültiger ID"""
        response = requests.get(f"{BASE_URL}/api/projects/invalid-id-12345")
        assert response.status_code == 404
        print("✓ GET /api/projects/invalid-id: 404 wie erwartet")

class TestPreviewInfo:
    """Preview Info Tests"""
    
    def test_get_preview_info(self):
        """Test GET /api/projects/{id}/preview-info"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/preview-info")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "has_preview" in data
        assert "ready_for_push" in data
        
        print(f"✓ GET /api/projects/{project_id}/preview-info:")
        print(f"  - has_preview: {data.get('has_preview')}")
        print(f"  - ready_for_push: {data.get('ready_for_push')}")
        print(f"  - entry_point: {data.get('entry_point')}")
        print(f"  - tested_features: {data.get('tested_features', [])}")

class TestAgents:
    """Agent Status Tests"""
    
    def test_get_agents(self):
        """Test GET /api/projects/{id}/agents"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/agents")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 7  # 7 Agenten erwartet
        
        agent_types = [a["agent_type"] for a in data]
        expected_agents = ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]
        
        for agent in expected_agents:
            assert agent in agent_types, f"Agent {agent} nicht gefunden"
        
        print(f"✓ GET /api/projects/{project_id}/agents: {len(data)} Agenten")
        for agent in data:
            print(f"  - {agent['agent_type']}: {agent['status']}")

class TestMessages:
    """Chat Messages Tests"""
    
    def test_get_messages(self):
        """Test GET /api/projects/{id}/messages"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/messages")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ GET /api/projects/{project_id}/messages: {len(data)} Nachrichten")

class TestFiles:
    """File System Tests"""
    
    def test_get_files(self):
        """Test GET /api/projects/{id}/files"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/files")
        assert response.status_code == 200
        data = response.json()
        
        assert "type" in data
        assert "tree" in data
        
        print(f"✓ GET /api/projects/{project_id}/files:")
        print(f"  - type: {data['type']}")
        print(f"  - tree items: {len(data.get('tree', []))}")

class TestRoadmapAndLogs:
    """Roadmap und Logs Tests"""
    
    def test_get_roadmap(self):
        """Test GET /api/projects/{id}/roadmap"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/roadmap")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ GET /api/projects/{project_id}/roadmap: {len(data)} Items")
    
    def test_get_logs(self):
        """Test GET /api/projects/{id}/logs"""
        # Get first available project
        projects_response = requests.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()
        
        if len(projects) == 0:
            pytest.skip("No projects available")
        
        project_id = projects[0]["id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/logs")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ GET /api/projects/{project_id}/logs: {len(data)} Log-Einträge")

class TestOllama:
    """Ollama Status Tests"""
    
    def test_ollama_status(self):
        """Test GET /api/ollama/status"""
        response = requests.get(f"{BASE_URL}/api/ollama/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "available" in data
        assert "models" in data
        
        print(f"✓ GET /api/ollama/status:")
        print(f"  - available: {data['available']}")
        print(f"  - models: {data['models']}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
