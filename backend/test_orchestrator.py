import asyncio
from app.agents.orchestrator import Orchestrator
from app.models.session import StudentSession

async def run_validation():
    print("--- Starting Task 1 Validation ---")
    orchestrator = Orchestrator()
    session_id = "test-session-123"
    
    # Test 1: Teaching Phase
    # We now properly instantiate the Pydantic model
    orchestrator.sessions[session_id] = StudentSession(
        session_id=session_id,
        active_phase="teaching"
    ) 
    
    target = await orchestrator.route_message(session_id, "Can you explain circles?")
    assert target == "tutor_agent", f"Failed Teaching Route. Got: {target}"
    print("✅ Test 1 Passed: Teaching routes to Tutor Agent")

    # Test 2: Practice Phase (Asking for help)
    # Update the attribute using dot notation
    orchestrator.sessions[session_id].active_phase = "practice"
    
    target = await orchestrator.route_message(session_id, "I need a hint for step 2")
    assert target == "tutor_agent", f"Failed Hint Route. Got: {target}"
    print("✅ Test 2 Passed: Hint requests route to Tutor Agent")

    # Test 3: Practice Phase (Submitting answer)
    target = await orchestrator.route_message(session_id, "My final answer is 42")
    assert target == "diagnostic_agent", f"Failed Diagnostic Route. Got: {target}"
    print("✅ Test 3 Passed: Answer submissions route to Diagnostic Agent")

    print("🎉 All Task 1 Validations Passed. Ready for Task 2.")

if __name__ == "__main__":
    asyncio.run(run_validation())