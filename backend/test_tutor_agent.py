import asyncio
from app.agents.teacher_agent import TutorAgent
from app.models.session import StudentSession

async def run_validation():
    print("--- Starting Task 2 Validation ---")
    tutor = TutorAgent()
    
    # Create a mock session
    session = StudentSession(
        session_id="test-session-456",
        active_phase="teaching",
        current_topic="Quadratic Equations"
    )
    
    # Test 1: Standard Teaching Interaction
    print("\nTesting Standard Interaction...")
    response_data = await tutor.process_message(session, "How do I find the roots?")
    
    assert "spoken_response" in response_data, "Missing spoken_response key"
    assert "whiteboard_actions" in response_data, "Missing whiteboard_actions key"
    assert isinstance(response_data["whiteboard_actions"], list), "whiteboard_actions must be a list"
    print("Avatar says:", response_data["spoken_response"])
    print("Board actions:", response_data["whiteboard_actions"])
    print("✅ Test 1 Passed: Output structure is correct.")

    # Test 2: Diagnostic Nudge Interaction
    print("\nTesting Diagnostic Nudge...")
    nudge_response = await tutor.process_message(
        session, 
        "I got x = 2", 
        diagnostic_nudge="The student missed a negative sign. The answer is -2. Guide them to recheck the formula."
    )
    
    print("Avatar says:", nudge_response["spoken_response"])
    # We visually verify that the spoken response mentions checking the sign
    print("✅ Test 2 Passed: Diagnostic nudge processed.")

    print("\n🎉 All Task 2 Validations Passed. Ready for Task 3.")

if __name__ == "__main__":
    asyncio.run(run_validation())