"""
SentinelOps-Lite AI Agent Gate
-------------------------------
This script runs as a step inside the Azure DevOps pipeline, AFTER the
unit tests have finished. It reads the test result summary, sends it
to Gemini (Google's AI model, via a Google AI Studio API key), and
asks it to make a simple go / no-go decision. The pipeline then reads
the agent's decision and either continues to deployment or stops.

This is intentionally simple so a beginner can read every line.
"""

import os
import sys
from google import genai

# 1. Read the test result summary that the pipeline saved to a file.
RESULTS_FILE = "test_results.txt"

if not os.path.exists(RESULTS_FILE):
    print(f"ERROR: {RESULTS_FILE} not found. Did the test step run first?")
    sys.exit(1)

with open(RESULTS_FILE, "r") as f:
    test_output = f.read()

# 2. Read the Google AI Studio (Gemini) API key from an environment variable.
#    In Azure DevOps this comes from a pipeline secret variable.
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY environment variable is not set.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# 3. Ask Gemini to review the test output and give a decision.
prompt = f"""
You are a release-approval agent for a CI/CD pipeline.
Below is the raw output of the automated test suite.

Rules:
- If ALL tests passed, respond APPROVE.
- If ANY test failed, respond REJECT.
- Respond with a single word only: APPROVE or REJECT.
- On a second line, give a one-sentence reason.

Test output:
{test_output}
"""

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=prompt,
)

decision_text = response.text.strip()
print("----- AI Agent Decision -----")
print(decision_text)
print("------------------------------")

# 4. Save the decision so the pipeline YAML can read it and branch on it.
decision_word = decision_text.splitlines()[0].strip().upper()

with open("agent_decision.txt", "w") as f:
    f.write(decision_word)

# 5. Exit with a failing code if the agent rejects, so the pipeline stage fails.
if decision_word != "APPROVE":
    print("Agent rejected the release. Stopping pipeline.")
    sys.exit(1)

print("Agent approved the release. Continuing to deployment.")
sys.exit(0)
