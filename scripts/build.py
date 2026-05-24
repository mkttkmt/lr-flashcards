#!/usr/bin/env python3
"""
LR JSON エクスポートから index.html を生成するスクリプト

入力: data/items.json (LRからエクスポートしたJSON)
出力: index.html
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "data" / "items.json"
OUTPUT_HTML = ROOT / "index.html"
TEMPLATE_HTML = ROOT / "scripts" / "template.html"

POS_MAP = {
    'NOUN': 'noun', 'PROPN': 'noun', 'VERB': 'verb', 'ADJ': 'adj',
    'ADV': 'adv', 'PRON': 'pron', 'DET': 'det', 'ADP': 'prep',
    'CCONJ': 'conj', 'SCONJ': 'conj', 'PART': 'part', 'INTJ': 'interj',
    'NUM': 'num', 'AUX': 'aux'
}

TOP_WORDS = 100
TOP_PHRASES = 20


def freq_label(rank):
    """LR の順位帯ラベル"""
    if rank <= 300:
        return "超頻出"
    if rank <= 600:
        return "頻出"
    if rank <= 900:
        return "標準"
    if rank <= 1700:
        return "やや稀"
    return "稀"


def trim(s, maxlen=200):
    if not s:
        return ''
    s = s.strip()
    if len(s) <= maxlen:
        return s
    cut = s[:maxlen]
    for sep in ['\n', '。', '. ', '! ', '? ']:
        idx = cut.rfind(sep)
        if idx > maxlen // 2:
            return cut[:idx + len(sep)].strip()
    return cut.strip() + '…'


def find_pos(tokens_dict, word):
    word_lower = word.lower()
    for sub_idx in ['0', '1', '2']:
        if sub_idx in tokens_dict:
            for tok in tokens_dict[sub_idx]:
                if (tok.get('lemma', {}).get('text', '').lower() == word_lower
                        or tok.get('form', {}).get('text', '').lower() == word_lower):
                    pos = tok.get('pos', '')
                    return POS_MAP.get(pos, pos.lower())
    return ''


def build_word_card(item):
    word = item.get('word', {}).get('text', '')
    base_track = (item.get('context', {})
                  .get('phrase', {}).get('reference', {})
                  .get('tm', {}).get('baseTrack', {}))
    is_machine_translated = base_track.get('langCode_G') == 'ja'

    phrase = item.get('context', {}).get('phrase', {})
    subtitles = phrase.get('subtitles', {})
    m_translations = phrase.get('mTranslations', {})
    h_translations = phrase.get('hTranslations') or {}
    tokens = phrase.get('subtitleTokens', {})

    ctx_en_parts = [subtitles[i] for i in ['0', '1', '2'] if i in subtitles]
    ctx_en = '\n'.join(ctx_en_parts)

    ctx_ja_parts = []
    for i in ['0', '1', '2']:
        if h_translations and i in h_translations and h_translations[i]:
            ctx_ja_parts.append(h_translations[i])
        elif i in m_translations and m_translations[i]:
            ctx_ja_parts.append(m_translations[i])
    ctx_ja = '\n'.join(ctx_ja_parts)

    pos = find_pos(tokens, word)
    title = phrase.get('reference', {}).get('diocoDocName', '')

    return {
        'k': word.lower(),          # storage key
        'tp': 'w',                   # type: word
        'w': word,                   # display text
        'p': pos,
        't': ', '.join(item.get('wordTranslationsArr', [])),
        'fr': item['freqRank'],
        'fl': freq_label(item['freqRank']),
        'ce': '' if is_machine_translated else trim(ctx_en, 180),
        'cj': trim(ctx_ja, 180),
        'src': title[:50],
        'mt': is_machine_translated,
    }


def build_phrase_card(item):
    phrase = item.get('context', {}).get('phrase', {})
    subtitles = phrase.get('subtitles', {})
    m_translations = phrase.get('mTranslations', {})
    h_translations = phrase.get('hTranslations') or {}

    # Main phrase text is at subtitles[1]
    phrase_text = subtitles.get('1', '').replace('\n', ' ').strip()
    # Translation: prefer human, fall back to machine
    if h_translations and h_translations.get('1'):
        phrase_trans = h_translations['1']
    else:
        phrase_trans = m_translations.get('1', '')

    title = phrase.get('reference', {}).get('diocoDocName', '')

    return {
        'k': phrase_text.lower(),    # storage key (full phrase lowercase)
        'tp': 'ph',                  # type: phrase
        'w': phrase_text,            # display text (full phrase)
        'p': 'phrase',
        't': phrase_trans,
        'fr': item['freqRank'],
        'fl': freq_label(item['freqRank']),
        'ce': '',                    # no example for phrases
        'cj': '',                    # no example for phrases
        'src': title[:50],
        'mt': False,                 # phrases shown as-is
    }


def extract_cards(items):
    # Split by itemType
    word_items = [i for i in items
                  if i.get('itemType') == 'WORD' and i.get('freqRank') is not None]
    phrase_items = [i for i in items
                    if i.get('itemType') == 'PHRASE']

    # Words: sort by freqRank ascending, dedupe by word lowercase, take top 100
    word_items.sort(key=lambda x: x['freqRank'])
    seen_words = set()
    unique_words = []
    for item in word_items:
        w = item.get('word', {}).get('text', '').lower()
        if w and w not in seen_words:
            seen_words.add(w)
            unique_words.append(item)
    top_words = unique_words[:TOP_WORDS]

    # Phrases: sort by timeCreated_ms ascending (oldest first), dedupe by phrase text lowercase, take top 20
    phrase_items.sort(key=lambda x: x.get('timeCreated_ms', 0))
    seen_phrases = set()
    unique_phrases = []
    for item in phrase_items:
        ph_text = item.get('context', {}).get('phrase', {}).get('subtitles', {}).get('1', '').replace('\n', ' ').strip().lower()
        if ph_text and ph_text not in seen_phrases:
            seen_phrases.add(ph_text)
            unique_phrases.append(item)
    top_phrases = unique_phrases[:TOP_PHRASES]

    cards = []
    for item in top_words:
        cards.append(build_word_card(item))
    for item in top_phrases:
        cards.append(build_phrase_card(item))

    return cards, len(top_words), len(top_phrases)


def main():
    if not INPUT_JSON.exists():
        print(f"❌ 入力JSONが見つかりません: {INPUT_JSON}", file=sys.stderr)
        sys.exit(1)
    if not TEMPLATE_HTML.exists():
        print(f"❌ テンプレートが見つかりません: {TEMPLATE_HTML}", file=sys.stderr)
        sys.exit(1)

    with INPUT_JSON.open('r', encoding='utf-8') as f:
        items = json.load(f)

    print(f"📂 LR JSON 読み込み: {len(items)} アイテム")

    cards, n_words, n_phrases = extract_cards(items)
    print(f"📌 抽出: 単語 {n_words} 語 + フレーズ {n_phrases} 件 = 合計 {len(cards)} カード")

    with TEMPLATE_HTML.open('r', encoding='utf-8') as f:
        template = f.read()

    cards_json = json.dumps(cards, ensure_ascii=False, separators=(',', ':'))

    if '{{CARDS_DATA}}' not in template:
        print("❌ テンプレートに {{CARDS_DATA}} プレースホルダーがありません", file=sys.stderr)
        sys.exit(1)

    html = template.replace('{{CARDS_DATA}}', cards_json)

    with OUTPUT_HTML.open('w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ 生成完了: {OUTPUT_HTML} ({len(html):,} chars)")


if __name__ == '__main__':
    main()
