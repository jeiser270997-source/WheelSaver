import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY no encontrada en el entorno.")

# Inicializar cliente de OpenAI apuntando a la API de DeepSeek V4
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

async def ask_deepseek_about_repos(question: str, repos: list[dict]) -> str:
    """
    Toma una pregunta del usuario y una lista de repositorios (obtenidos de la DB local),
    y usa DeepSeek V4 para razonar y dar una respuesta experta.
    """
    # Formatear el contexto
    context = ""
    for r in repos:
        context += f"- {r['owner']}/{r['name']} ({r.get('stars', 0)}⭐): {r.get('description', 'Sin descripción')}. Lenguaje: {r.get('language', '-')}\n"
    
    if not context:
        context = "No se encontraron repositorios relevantes en la base de datos."

    system_prompt = """Eres WheelSaver AI, un ingeniero de software senior altamente experimentado (con capacidades de DeepSeek V4).
Tu objetivo es analizar la pregunta del usuario y responder recomendando los mejores repositorios basándote estrictamente en el contexto proporcionado (los resultados de la base de datos local).
Sé directo, explica brevemente por qué recomiendas una librería sobre otra, y usa un formato Markdown limpio."""

    user_prompt = f"""Pregunta del usuario: "{question}"

Contexto extraído de la base de datos de WheelSaver:
{context}

Por favor, analiza estos repositorios y responde a la pregunta de la mejor manera posible."""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",  # Model Identifier for DeepSeek V3/V4 (deepseek-chat maps to the latest fast model)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error al comunicarse con DeepSeek: {e}"
