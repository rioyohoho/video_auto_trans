from src.utils import logger as log
from .useAI import request

TAB = 3
def translates(texts: str | list[str], tar_lang=None, from_lang='auto') -> list[str]|str:
    if not tar_lang: raise ValueError('tar_lang is None!')
    result = ai_translation(texts=texts, tar_lang=tar_lang, trials=3)
    if result: return result.split('\n')
    log.ln('USE default GoogleTranslator', log.GR, TAB)
    return text_translation(text=texts, from_lang=from_lang, tar_lang=tar_lang)

def ai_translation(texts: str | list[str], tar_lang=None, trials=3):
    prompt= f"""
    You are an professional translator. Use clear and natural language.
    Translate the following lines into {tar_lang}.
    
    Strict Requirements:
    1. Maintain the specific pitch of the 'general' genre.
    2. Ensure the output has the same number of lines as the input.
    3. No explanations or extra text.

    Content:
    {"\n".join(texts)}
    """
    return request(prompt=prompt, trials=trials, tab=TAB)

from deep_translator import GoogleTranslator
def text_translation(text: str | list[str], from_lang:str='auto', tar_lang:str=None, max_char:int=1e3) -> str | list[str]:
    translator = GoogleTranslator(source=from_lang, target=tar_lang)
    if isinstance(text, str): return translator.translate(text)
    results, chunk, length = [], [], 0
    total_input = len(text)
    for i, line in enumerate(text):
        if length + len(line) + 1 > max_char and chunk:
            log.pr(i, total_input, txt=f"Translating({from_lang}:{tar_lang})...")
            res = translator.translate('\n'.join(chunk))
            translated_lines = res.split('\n')
            while len(translated_lines) < len(chunk):translated_lines.append("")
            results.extend(translated_lines[:len(chunk)])
            chunk, length = [], 0
        chunk.append(line)
        length += len(line) + 1
    log.pr(total_input, total_input, txt=f"Translating({from_lang}:{tar_lang})...\n", bar_color=log.G)
    if chunk:
        res = translator.translate('\n'.join(chunk))
        translated_lines = res.split('\n')
        while len(translated_lines) < len(chunk):
            translated_lines.append("")
        results.extend(translated_lines[:len(chunk)])
    return results
