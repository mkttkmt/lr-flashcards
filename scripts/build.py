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

TOP_N = 100


def freq_label(rank):
    """LR の順位帯ラベルにマッピング"""
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
    """subtitleTokens から target word の品詞を探す"""
    word_lower = word.lower()
    for sub_idx in ['0', '1', '2']:
        if sub_idx in tokens_dict:
            for tok in tokens_dict[sub_idx]:
                if (tok.get('lemma', {}).get('text', '').lower() == word_lower
                        or tok.get('form', {}).get('text', '').lower() == word_lower):
                    pos = tok.get('pos', '')
                    return POS_MAP.get(pos, pos.lower())
    return ''


def extract_cards(items):
    """JSONアイテムからフラッシュカード用データを抽出"""
    # freqRank が無いものは除外、ランク昇順でソート
    items_with_rank = [item for item in items if item.get('freqRank') is not None]
    items_with_rank.sort(key=lambda x: x['freqRank'])

    # 単語で重複排除
    seen = set()
    unique = []
    for item in items_with_rank:
        word = item.get('word', {}).get('text', '').lower()
        if word and word not in seen:
            seen.add(word)
            unique.append(item)

    top = unique[:TOP_N]

    cards = []
    for item in top:
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

        # 英語コンテキスト
        ctx_en_parts = [subtitles[i] for i in ['0', '1', '2'] if i in subtitles]
        ctx_en = '\n'.join(ctx_en_parts)

        # 日本語コンテキスト: human translation を優先、無ければ machine
        ctx_ja_parts = []
        for i in ['0', '1', '2']:
            if h_translations and i in h_translations and h_translations[i]:
                ctx_ja_parts.append(h_translations[i])
            elif i in m_translations and m_translations[i]:
                ctx_ja_parts.append(m_translations[i])
        ctx_ja = '\n'.join(ctx_ja_parts)

        pos = find_pos(tokens, word)
        title = phrase.get('reference', {}).get('diocoDocName', '')

        cards.append({
            'w': word,
            'p': pos,
            't': ', '.join(item.get('wordTranslationsArr', [])),
            'fr': item['freqRank'],
            'fl': freq_label(item['freqRank']),
            'ce': '' if is_machine_translated else trim(ctx_en, 180),
            'cj': trim(ctx_ja, 180),
            'src': title[:50],
            'mt': is_machine_translated,
        })
    return cards


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

    cards = extract_cards(items)
    print(f"📌 抽出: 上位 {len(cards)} 語 (freqRank {cards[0]['fr']}〜{cards[-1]['fr']})")

    # テンプレート読み込み + データ差し込み
    with TEMPLATE_HTML.open('r', encoding='utf-8') as f:
        template = f.read()

    cards_json = json.dumps(cards, ensure_ascii=False, separators=(',', ':'))

    # テンプレート内の {{CARDS_DATA}} プレースホルダーを置換
    if '{{CARDS_DATA}}' not in template:
        print("❌ テンプレートに {{CARDS_DATA}} プレースホルダーがありません", file=sys.stderr)
        sys.exit(1)

    html = template.replace('{{CARDS_DATA}}', cards_json)

    with OUTPUT_HTML.open('w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ 生成完了: {OUTPUT_HTML} ({len(html):,} chars)")


if __name__ == '__main__':
    main()
