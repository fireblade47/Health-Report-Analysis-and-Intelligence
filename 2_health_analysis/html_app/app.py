"""Local HTTP server for the HTML blood-work analysis application."""

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent.parent

EXTRACTION_PROMPT = """
You are a medical data extraction assistant.

From the medical report below, extract every reported test value and classify it as
HIGH, LOW, or NORMAL strictly according to the reference range stated in the report.
If a value cannot be classified from the supplied range, state NOT DETERMINED.
Do not make up reference ranges or diagnoses.

Return Markdown only, with this exact structure:
## Test results
| Test name | Value | Status | Reference range |
| --- | --- | --- | --- |

Blood report:
{blood_report}
"""

DIET_PROMPT = """
You are a clinical nutritionist familiar with Indian dietary habits.

Using only the blood-work analysis below, write:
1. A simple, non-alarmist health summary in 4–5 lines.
2. A practical Indian diet plan with exactly these two headings: "Foods to avoid"
   and "Foods to eat more of".

Do not diagnose, prescribe medication, or recommend changing medicines. Mention that
the person should discuss abnormal findings with their clinician.

Blood-work analysis:
{extracted_values}
"""


def get_llm(provider: str, model: str):
    if provider == "groq":
        from langchain_groq import ChatGroq

        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("Set GROQ_API_KEY in the project .env file before using Groq.")
        return ChatGroq(model=model, reasoning_format="parsed")

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Set GOOGLE_API_KEY in the project .env file before using Gemini.")
        return ChatGoogleGenerativeAI(model=model)

    raise ValueError("Choose either Groq or Gemini.")


def response_text(response) -> str:
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def analyse_report(report: str, provider: str, model: str) -> dict[str, str]:
    llm = get_llm(provider, model)
    extracted_values = response_text(
        llm.invoke(EXTRACTION_PROMPT.format(blood_report=report))
    )
    diet_plan = response_text(llm.invoke(DIET_PROMPT.format(extracted_values=extracted_values)))
    return {"extracted_values": extracted_values, "diet_plan": diet_plan}


class AppHandler(SimpleHTTPRequestHandler):
    """Serve static files plus a JSON endpoint for the LLM analysis."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/analyze":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 1_000_000:
                raise ValueError("The report is too large. Limit it to 1 MB.")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            report = payload.get("report", "").strip()
            provider = payload.get("provider", "groq")
            model = payload.get("model", "").strip()
            if not report:
                raise ValueError("Paste or upload a blood report before analysing it.")
            if not model:
                raise ValueError("Enter a model name.")
            self.send_json(HTTPStatus.OK, analyse_report(report, provider, model))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Analysis could not be completed. Check the provider, model, and API key."},
            )

    def send_json(self, status: HTTPStatus, payload: dict[str, str]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), AppHandler)
    print("Blood Work Analyzer is running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
