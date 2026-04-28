from vertexai.generative_models import GenerativeModel
import vertexai

vertexai.init(
    project="mathverse-live-ai",
    location="global"
)

model = GenerativeModel("gemini-2.5-pro")

res = model.generate_content("Solve x^2 - 4 = 0")

print(res.text)