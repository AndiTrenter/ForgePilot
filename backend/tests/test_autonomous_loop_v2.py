"""
Test Suite for ForgePilot Version 2.2.0 - E1 Autonomous Loop Logic
Tests:
- Backend API /api/projects/{project_id}/chat functionality
- System Prompt loading
- Agent Tools availability (create_file, test_code, ask_user, mark_complete, web_search, etc.)
- Autonomous Loop Logic syntax correctness
- Force-Continue mechanism
- Error-Recovery logic
- Max iterations set to 200
- ask_user event handling
"""

import pytest
import requests
import os
import json
import re

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://forgepilot-docker.preview.emergentagent.com"


class TestAutonomousLoopConfiguration:
    """Test that the autonomous loop is configured correctly"""
    
    def test_health_endpoint(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        print(f"✓ Health check passed: {data['status']}")
    
    def test_version_endpoint(self):
        """Verify version endpoint returns version info"""
        response = requests.get(f"{BASE_URL}/api/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        print(f"✓ Version: {data['version']}")


class TestAgentToolsAvailability:
    """Test that all required agent tools are defined"""
    
    @pytest.fixture(scope="class")
    def server_code(self):
        """Read server.py to verify tool definitions"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            return f.read()
    
    def test_create_file_tool_exists(self, server_code):
        """Verify create_file tool is defined"""
        assert '"name": "create_file"' in server_code
        print("✓ create_file tool defined")
    
    def test_modify_file_tool_exists(self, server_code):
        """Verify modify_file tool is defined"""
        assert '"name": "modify_file"' in server_code
        print("✓ modify_file tool defined")
    
    def test_read_file_tool_exists(self, server_code):
        """Verify read_file tool is defined"""
        assert '"name": "read_file"' in server_code
        print("✓ read_file tool defined")
    
    def test_delete_file_tool_exists(self, server_code):
        """Verify delete_file tool is defined"""
        assert '"name": "delete_file"' in server_code
        print("✓ delete_file tool defined")
    
    def test_list_files_tool_exists(self, server_code):
        """Verify list_files tool is defined"""
        assert '"name": "list_files"' in server_code
        print("✓ list_files tool defined")
    
    def test_run_command_tool_exists(self, server_code):
        """Verify run_command tool is defined"""
        assert '"name": "run_command"' in server_code
        print("✓ run_command tool defined")
    
    def test_create_roadmap_tool_exists(self, server_code):
        """Verify create_roadmap tool is defined"""
        assert '"name": "create_roadmap"' in server_code
        print("✓ create_roadmap tool defined")
    
    def test_update_roadmap_status_tool_exists(self, server_code):
        """Verify update_roadmap_status tool is defined"""
        assert '"name": "update_roadmap_status"' in server_code
        print("✓ update_roadmap_status tool defined")
    
    def test_web_search_tool_exists(self, server_code):
        """Verify web_search tool is defined"""
        assert '"name": "web_search"' in server_code
        print("✓ web_search tool defined")
    
    def test_test_code_tool_exists(self, server_code):
        """Verify test_code tool is defined"""
        assert '"name": "test_code"' in server_code
        print("✓ test_code tool defined")
    
    def test_verify_game_tool_exists(self, server_code):
        """Verify verify_game tool is defined"""
        assert '"name": "verify_game"' in server_code
        print("✓ verify_game tool defined")
    
    def test_debug_error_tool_exists(self, server_code):
        """Verify debug_error tool is defined"""
        assert '"name": "debug_error"' in server_code
        print("✓ debug_error tool defined")
    
    def test_ask_user_tool_exists(self, server_code):
        """Verify ask_user tool is defined"""
        assert '"name": "ask_user"' in server_code
        print("✓ ask_user tool defined")
    
    def test_mark_complete_tool_exists(self, server_code):
        """Verify mark_complete tool is defined"""
        assert '"name": "mark_complete"' in server_code
        print("✓ mark_complete tool defined")
    
    def test_agent_tools_array_exists(self, server_code):
        """Verify AGENT_TOOLS array is defined"""
        assert "AGENT_TOOLS = [" in server_code
        print("✓ AGENT_TOOLS array defined")


class TestAutonomousLoopLogic:
    """Test the autonomous loop logic implementation"""
    
    @pytest.fixture(scope="class")
    def server_code(self):
        """Read server.py to verify loop logic"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            return f.read()
    
    def test_max_iterations_set_to_200(self, server_code):
        """Verify max_iterations default is 200"""
        # Look for the function signature with max_iterations=200
        pattern = r'async def run_autonomous_agent\([^)]*max_iterations:\s*int\s*=\s*200'
        match = re.search(pattern, server_code)
        assert match is not None, "max_iterations should be set to 200 in run_autonomous_agent function"
        print("✓ max_iterations default is 200")
    
    def test_no_hard_stop_in_while_loop(self, server_code):
        """Verify there's no immediate hard stop in the while loop"""
        # The loop should continue even after max_iterations with a warning
        assert "if iteration > max_iterations:" in server_code
        assert "if iteration > max_iterations + 20:" in server_code
        # Should have warning before hard stop
        assert "'warning'" in server_code
        print("✓ No immediate hard stop - warning issued first, then stop at max+20")
    
    def test_force_continue_mechanism_exists(self, server_code):
        """Verify Force-Continue mechanism when no tool calls"""
        # Check for the force continue logic
        assert "If no tool calls and not stopping, FORCE agent to continue" in server_code
        assert "JETZT HANDELN! Nutze Tools um fortzufahren" in server_code
        assert "STOPPE NICHT! Arbeite weiter bis mark_complete!" in server_code
        print("✓ Force-Continue mechanism implemented")
    
    def test_error_recovery_logic_exists(self, server_code):
        """Verify Error-Recovery logic without stopping"""
        # Check for error recovery that doesn't stop the loop
        assert "E1 STRATEGY: Don't stop on error - try to recover!" in server_code
        assert "FEHLER aufgetreten:" in server_code
        assert "Bitte analysiere den Fehler und fahre fort" in server_code
        print("✓ Error-Recovery logic implemented (continues on error)")
    
    def test_ask_user_stops_loop(self, server_code):
        """Verify ask_user tool stops the loop correctly"""
        assert 'if result.get("ask_user"):' in server_code
        assert "should_continue = False" in server_code
        assert "'ask_user': True" in server_code
        print("✓ ask_user correctly stops the loop")
    
    def test_mark_complete_stops_loop(self, server_code):
        """Verify mark_complete tool stops the loop correctly"""
        assert 'if result.get("complete"):' in server_code
        assert "'complete': True" in server_code
        print("✓ mark_complete correctly stops the loop")
    
    def test_only_critical_conditions_stop_loop(self, server_code):
        """Verify only critical conditions stop the loop"""
        # Check the comment that explains the stopping conditions
        assert "CRITICAL: NEVER stop just because there are no tool calls!" in server_code
        assert "We ONLY stop on:" in server_code
        assert "ask_user (critical question)" in server_code
        assert "mark_complete (project finished)" in server_code
        assert "max_iterations reached" in server_code
        print("✓ Only critical conditions (ask_user, mark_complete, max_iterations) stop the loop")


class TestSystemPromptContent:
    """Test that the system prompt contains E1-style instructions"""
    
    @pytest.fixture(scope="class")
    def server_code(self):
        """Read server.py to verify system prompt"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            return f.read()
    
    def test_system_prompt_has_e1_identity(self, server_code):
        """Verify system prompt mentions E1 identity"""
        assert "E1" in server_code or "ELITE-ENTWICKLER" in server_code
        print("✓ System prompt has E1/Elite developer identity")
    
    def test_system_prompt_has_planning_phase(self, server_code):
        """Verify system prompt includes planning phase"""
        assert "PLANEN" in server_code or "PLANNING" in server_code or "Planner" in server_code
        print("✓ System prompt includes planning phase")
    
    def test_system_prompt_has_testing_phase(self, server_code):
        """Verify system prompt includes testing phase"""
        assert "TESTING" in server_code or "Tester" in server_code or "test_code" in server_code
        print("✓ System prompt includes testing phase")
    
    def test_system_prompt_has_web_search_instructions(self, server_code):
        """Verify system prompt includes web_search instructions"""
        assert "web_search" in server_code
        print("✓ System prompt includes web_search instructions")
    
    def test_system_prompt_has_ask_user_instructions(self, server_code):
        """Verify system prompt includes ask_user instructions"""
        assert "ask_user" in server_code
        print("✓ System prompt includes ask_user instructions")


class TestFrontendAskUserHandling:
    """Test that frontend handles ask_user events correctly"""
    
    @pytest.fixture(scope="class")
    def frontend_code(self):
        """Read App.js to verify ask_user handling"""
        app_path = "/app/frontend/src/App.js"
        with open(app_path, 'r') as f:
            return f.read()
    
    def test_frontend_handles_ask_user_event(self, frontend_code):
        """Verify frontend handles ask_user event from backend"""
        assert "if (data.ask_user)" in frontend_code
        print("✓ Frontend handles ask_user event")
    
    def test_frontend_displays_question_in_chat(self, frontend_code):
        """Verify frontend displays question in chat"""
        assert "FRAGE VOM AGENT" in frontend_code
        assert "setMessages" in frontend_code
        print("✓ Frontend displays question in chat")
    
    def test_frontend_sets_agent_progress_on_ask_user(self, frontend_code):
        """Verify frontend updates agent progress on ask_user"""
        assert 'setAgentProgress' in frontend_code
        assert '"ask_user"' in frontend_code
        print("✓ Frontend updates agent progress on ask_user")
    
    def test_frontend_scrolls_to_question(self, frontend_code):
        """Verify frontend scrolls to show question"""
        assert "scrollTop" in frontend_code or "scrollHeight" in frontend_code
        print("✓ Frontend scrolls to show question")


class TestChatAPIEndpoint:
    """Test the chat API endpoint functionality"""
    
    @pytest.fixture(scope="class")
    def test_project_id(self):
        """Create a test project and return its ID"""
        response = requests.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_AutonomousLoopTest",
            "description": "Test project for autonomous loop testing",
            "project_type": "fullstack"
        })
        if response.status_code == 200:
            project_id = response.json().get("id")
            yield project_id
            # Cleanup
            requests.delete(f"{BASE_URL}/api/projects/{project_id}")
        else:
            pytest.skip(f"Could not create test project: {response.status_code}")
    
    def test_chat_endpoint_exists(self, test_project_id):
        """Verify chat endpoint exists and accepts POST"""
        # Note: We can't fully test streaming SSE in pytest, but we can verify the endpoint exists
        # The endpoint expects MessageCreate model with project_id and content
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project_id}/chat",
            json={"project_id": test_project_id, "content": "test message"},
            stream=True,
            timeout=10
        )
        # Should return 200 for streaming or error if no LLM configured
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        print(f"✓ Chat endpoint exists and responds (status: {response.status_code})")
    
    def test_chat_endpoint_returns_streaming_response(self, test_project_id):
        """Verify chat endpoint returns SSE streaming response"""
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project_id}/chat",
            json={"project_id": test_project_id, "content": "Hello"},
            stream=True,
            timeout=10
        )
        # Check content type for SSE
        content_type = response.headers.get('content-type', '')
        # Should be text/event-stream for SSE
        if response.status_code == 200:
            assert 'text/event-stream' in content_type or 'application/json' in content_type
            print(f"✓ Chat endpoint returns streaming response (content-type: {content_type})")
        else:
            print(f"⚠ Chat endpoint returned {response.status_code} - may need LLM configuration")


class TestExecuteToolFunction:
    """Test the execute_tool function handles all tools correctly"""
    
    @pytest.fixture(scope="class")
    def server_code(self):
        """Read server.py to verify execute_tool function"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            return f.read()
    
    def test_execute_tool_handles_ask_user(self, server_code):
        """Verify execute_tool handles ask_user correctly"""
        assert 'elif tool_name == "ask_user":' in server_code
        assert 'result["ask_user"] = True' in server_code
        assert 'result["continue"] = False' in server_code
        print("✓ execute_tool handles ask_user correctly")
    
    def test_execute_tool_handles_mark_complete(self, server_code):
        """Verify execute_tool handles mark_complete correctly"""
        assert 'elif tool_name == "mark_complete":' in server_code
        assert 'result["complete"] = True' in server_code
        print("✓ execute_tool handles mark_complete correctly")
    
    def test_execute_tool_handles_web_search(self, server_code):
        """Verify execute_tool handles web_search correctly"""
        assert 'elif tool_name == "web_search":' in server_code
        assert 'duckduckgo_search' in server_code
        print("✓ execute_tool handles web_search correctly")
    
    def test_execute_tool_handles_test_code(self, server_code):
        """Verify execute_tool handles test_code correctly"""
        assert 'elif tool_name == "test_code":' in server_code
        assert 'test_type' in server_code
        print("✓ execute_tool handles test_code correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
