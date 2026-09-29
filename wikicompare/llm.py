"""Optional AI step: ask Claude for an outline that closes the gaps."""
import os


def suggest_outline(topic, missing_sections, missing_fields, target_lang, ref_lang):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY (see .env.example) to use this feature.")
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    prompt = (
        f"The {target_lang} Wikipedia article on '{topic}' is shorter than the {ref_lang} one.\n"
        f"Sections it lacks: {missing_sections or 'none'}\n"
        f"Infobox fields it lacks: {missing_fields or 'none'}\n\n"
        f"Write a concise outline (headings plus 1-2 lines each) an editor could follow to "
        f"expand the {target_lang} article. Write headings in {target_lang}. "
        "Do not invent facts; say what kind of information each section needs."
    )
    msg = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5"),
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")
