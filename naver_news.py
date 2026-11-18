import os
import requests
from bs4 import BeautifulSoup

SEEN_FILE = "seen_links.txt"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def crawl_naver_news(query: str) -> list[dict[str, str]]:
    url = "https://search.naver.com/search.naver"
    params = {
        "ssc": "tab.news.all",
        "where": "news",
        "query": query,
        "sort": "1",  # 1: 최신순
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    for title_link in soup.select('a[data-heatmap-target=".tit"]'):
        title_span = title_link.select_one("span.sds-comps-text")
        title = (
            title_span.get_text(strip=True)
            if title_span
            else title_link.get_text(strip=True)
        )
        link = title_link.get("href", "")

        card = title_link.parent
        while card and not card.select_one('[data-sds-comp="Profile"]'):
            card = card.parent

        press = ""
        if card:
            press_box = card.select_one(".sds-comps-profile-info-title-text")
            if press_box:
                inner_span = press_box.select_one("a span.sds-comps-text")
                press = (
                    inner_span.get_text(strip=True)
                    if inner_span
                    else press_box.get_text(strip=True)
                )

        articles.append({"title": title, "press": press, "link": link})

    return articles


def load_seen_links() -> set[str]:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_seen_links(links: set[str]) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for link in sorted(links):
            f.write(link + "\n")


def send_discord(message: str) -> None:
    requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)


if __name__ == "__main__":
    seen = load_seen_links()
    articles = crawl_naver_news("엘앤에프")

    # 맨 처음 실행할 때는 알림 폭탄을 막기 위해 목록만 저장
    if not seen:
        seen = {a["link"] for a in articles}
        save_seen_links(seen)
        print(f"첫 실행 완료: 기준 기사 {len(seen)}건을 저장했습니다.")
    else:
        new_articles = [a for a in articles if a["link"] not in seen]
        for a in new_articles:
            msg = f"📰 **{a['title']}**\n언론사: {a['press']}\n{a['link']}"
            send_discord(msg)
            seen.add(a["link"])
            print("알림 전송:", a["title"])

        if new_articles:
            save_seen_links(seen)
