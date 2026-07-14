"""
SentinelOps-Lite AI Pipeline Reviewer
---------------------------------------
This script runs as the LAST stage of the pipeline, with condition: always(),
meaning it runs whether every previous stage succeeded OR failed.

Its job is different from agent.py (the pre-deploy APPROVE/REJECT gate):
this script looks back at the WHOLE pipeline run and produces a review:

  - If something failed: explains the issue, the likely root cause, and a
    concrete fix.
  - If everything succeeded: summarizes what was checked/validated, and
    offers a couple of specific enhancement suggestions - or explains why
    the current process is already solid, if there's nothing meaningful
    to add.

The result is printed to the pipeline logs AND saved as a markdown file
(pipeline-review.md) that gets published as a downloadable build artifact.
"""

import os
import sys
from google import genai

# ---------------------------------------------------------------------
# 1. Gather stage results (passed in as env vars from the YAML)
# ---------------------------------------------------------------------
build_test_result = os.environ.get("BUILD_TEST_RESULT", "Unknown")
ai_gate_result = os.environ.get("AI_GATE_RESULT", "Unknown")
deploy_result = os.environ.get("DEPLOY_RESULT", "Unknown")

# ---------------------------------------------------------------------
# 2. Gather whatever log/output files are available (some may be missing
#    if that stage never ran, e.g. Deploy never happens if tests failed)
# ---------------------------------------------------------------------
def read_if_exists(path, max_chars=3000):
    if os.path.exists(path):
        with open(path, "r", errors="ignore") as f:
            content = f.read()
        # Keep the LAST part of long logs - that's usually where the
        # real error is, not the setup noise at the top.
        return content[-max_chars:]
    return None

test_output = read_if_exists("test_results.txt")
deploy_log = read_if_exists("deploy_log.txt")
agent_decision = read_if_exists("agent_decision.txt")

# ---------------------------------------------------------------------
# 3. Read the Google AI Studio (Gemini) API key
# ---------------------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY environment variable is not set.")
    # This stage is informational - we still exit 0 so it never blocks
    # or fails the pipeline on its own.
    sys.exit(0)

client = genai.Client(api_key=api_key)

# ---------------------------------------------------------------------
# 4. Build the prompt
# ---------------------------------------------------------------------
overall_status = "FAILED" if "Failed" in (build_test_result, ai_gate_result, deploy_result) else "SUCCESS"

prompt = f"""
You are a senior DevOps engineer reviewing a completed CI/CD pipeline run.
Be specific and concise. Reference actual details from the logs below when
you can - do not give generic advice that could apply to any pipeline.

STAGE RESULTS:
- Build & Test: {build_test_result}
- AI Agent Gate (pre-deploy approval): {ai_gate_result}
- Deploy to AWS: {deploy_result}

TEST OUTPUT (may be partial):
{test_output or "Not available - this stage may not have run."}

AI AGENT GATE DECISION (from the pre-deploy check):
{agent_decision or "Not available - this stage may not have run."}

DEPLOY LOG (tail end, may be partial):
{deploy_log or "Not available - this stage may not have run."}

INSTRUCTIONS:
Overall pipeline status is: {overall_status}

If overall status is FAILED, respond in EXACTLY this structure:
ISSUE: <one line describing what failed>
ROOT CAUSE: <1-2 sentences, specific, reference the actual error text if visible above>
FIX: <concrete, actionable steps a developer should take right now>

If overall status is SUCCESS, respond in EXACTLY this structure:
REVIEWED: <1-2 sentences on what was actually checked/validated this run>
SUGGESTIONS: <1-3 specific, non-generic enhancement ideas relevant to what you saw - or write "None right now" if the pipeline is well-covered>
WHY CURRENT PROCESS IS SOLID: <1-2 sentences justifying the current setup>

Keep the entire response under 200 words. Do not add commentary outside this structure.
"""

# ---------------------------------------------------------------------
# 5. Ask Gemini for the review
# ---------------------------------------------------------------------
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

review_text = response.text.strip()

print("=" * 60)
print(f"AI PIPELINE REVIEW - Overall status: {overall_status}")
print("=" * 60)
print(review_text)
print("=" * 60)

# ---------------------------------------------------------------------
# 6. Save as a markdown file so it can be published as a build artifact
#    and viewed/downloaded from the Azure DevOps pipeline run page.
# ---------------------------------------------------------------------
with open("pipeline-review.md", "w") as f:
    f.write(f"# AI Pipeline Review\n\n")
    f.write(f"**Overall status:** {overall_status}\n\n")
    f.write(f"| Stage | Result |\n|---|---|\n")
    f.write(f"| Build & Test | {build_test_result} |\n")
    f.write(f"| AI Agent Gate | {ai_gate_result} |\n")
    f.write(f"| Deploy to AWS | {deploy_result} |\n\n")
    f.write("## Review\n\n")
    f.write(review_text + "\n")

print("\nSaved full review to pipeline-review.md (published as a build artifact).")

# This stage never fails the pipeline - it's informational only.
sys.exit(0)
