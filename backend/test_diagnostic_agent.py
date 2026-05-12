import asyncio
from app.agents.diagnostic_agent import DiagnosticAgent
from app.models.session import StudentSession

async def run_validation():
    print("--- Starting Task 3 Validation ---")
    diagnostic = DiagnosticAgent()
    session = StudentSession(session_id="test-session-789", active_phase="practice")
    correct_answer = "42"
    
    # Test 1: Correct Answer
    print("\nTesting Correct Answer...")
    res_correct = await diagnostic.evaluate_answer(session, "42", correct_answer)
    assert res_correct["is_correct"] is True, "Failed: Should be marked correct."
    assert res_correct["error_category"] == "none", "Failed: Category should be none."
    print("✅ Test 1 Passed: Correct answer verified.")

    # Test 2: Sign Error
    print("\nTesting Sign Error...")
    res_sign = await diagnostic.evaluate_answer(session, "-42", correct_answer)
    assert res_sign["is_correct"] is False, "Failed: Should be marked incorrect."
    assert res_sign["error_category"] == "sign_error", "Failed: Should detect sign error."
    print("Hidden Nudge Generated:", res_sign["hidden_nudge"])
    print("✅ Test 2 Passed: Sign error diagnosed.")

    # Test 3: General Calculation Error
    print("\nTesting General Error...")
    res_calc = await diagnostic.evaluate_answer(session, "100", correct_answer)
    assert res_calc["is_correct"] is False, "Failed: Should be marked incorrect."
    assert res_calc["error_category"] == "calculation_error", "Failed: Should be a calculation error."
    print("Hidden Nudge Generated:", res_calc["hidden_nudge"])
    print("✅ Test 3 Passed: General error diagnosed.")

    print("\n🎉 All Task 3 Validations Passed. Ready for the WebSockets Wiring.")

if __name__ == "__main__":
    asyncio.run(run_validation())