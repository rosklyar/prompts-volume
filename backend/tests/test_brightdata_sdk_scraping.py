"""Exploration tests for BrightData SDK scraping capabilities."""
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.skip(reason="SDK exploration - requires BrightData API key. Run manually.")
@pytest.mark.asyncio
async def test_scrape_chatgpt_with_brightdata_sdk():
    """Test scraping ChatGPT prompt response using BrightData SDK.

    To run: uv run pytest tests/test_brightdata_sdk_scraping.py::test_scrape_chatgpt_with_brightdata_sdk -v -s
    """
    from brightdata import BrightDataClient
    from brightdata.payloads import ChatGPTPromptPayload

    async with BrightDataClient(token="7aef23ce-b960-4864-915e-92cef2ba7f1e") as client:
        payload = ChatGPTPromptPayload(
            prompt="What are the top 3 programming languages in 2024?",
            web_search=True
        )

        result = await client.scrape.chatgpt.prompt(**payload.to_dict())

        print("\n=== ChatGPT Scrape Result ===")
        print(f"Success: {result.success}")
        if result.success and result.data:
            print(f"Answer: {result.data[0]['answer_text']}")
            print(f"Cost: ${result.cost:.4f}")
        else:
            print(f"Error: {result.error}")


@pytest.mark.skip(reason="SDK exploration - requires BrightData API key. Run manually.")
@pytest.mark.asyncio
async def test_scrape_chatgpt_batch_ua():
    """Test scraping ChatGPT with Ukrainian prompts (async parallel).

    To run: uv run pytest tests/test_brightdata_sdk_scraping.py::test_scrape_chatgpt_batch_ua -v -s
    """
    import asyncio
    import time
    from brightdata import BrightDataClient
    from brightdata.payloads import ChatGPTPromptPayload

    prompts = [
        "Порекомендуй MacBook для роботи з фото",
        "Порадь моноблок для дому",
        "Склади список найкращих ПК для бюджету 30 тис. грн",
    ]

    async with BrightDataClient(token="7aef23ce-b960-4864-915e-92cef2ba7f1e") as client:

        async def fetch_prompt(prompt_text: str) -> tuple[str, object, float]:
            start = time.time()
            payload = ChatGPTPromptPayload(
                prompt=prompt_text,
                web_search=True,
                country="UA",
            )
            result = await client.scrape.chatgpt.prompt(**payload.to_dict(), poll_timeout=300)
            elapsed = time.time() - start
            return prompt_text, result, elapsed

        print("\n=== ChatGPT UA Results (Async Parallel) ===")
        total_start = time.time()

        results = await asyncio.gather(*[fetch_prompt(p) for p in prompts])

        total_elapsed = time.time() - total_start
        total_cost = 0.0

        for i, (prompt_text, result, elapsed) in enumerate(results):
            print(f"\n--- Prompt {i + 1}: {prompt_text} ---")
            print(f"Time: {elapsed:.2f}s | Success: {result.success}")
            if result.success and result.data:
                print(f"Answer: {result.data[0]['answer_text'][:300]}...")
                if result.cost:
                    total_cost += result.cost
            else:
                print(f"Error: {result.error}")

        print(f"\n=== Total Time: {total_elapsed:.2f}s | Total Cost: ${total_cost:.4f} ===")


@pytest.mark.skip(reason="SDK exploration - requires BrightData API key. Run manually.")
@pytest.mark.asyncio
async def test_scrape_perplexity_with_brightdata_sdk():
    """Test scraping Perplexity using BrightData SDK scrape_url.

    Note: SDK doesn't have a dedicated Perplexity scraper (only chatgpt, amazon,
    facebook, instagram, linkedin). Using generic scrape_url instead.

    To run: uv run pytest tests/test_brightdata_sdk_scraping.py::test_scrape_perplexity_with_brightdata_sdk -v -s
    """
    from brightdata import BrightDataClient

    async with BrightDataClient(token="7aef23ce-b960-4864-915e-92cef2ba7f1e") as client:
        result = await client.scrape_url("https://www.perplexity.ai/")

        print("\n=== Perplexity Scrape Result ===")
        print(f"Success: {result.success}")
        if result.success and result.data:
            print(f"Data length: {len(str(result.data))} chars")
            print(f"Data preview: {str(result.data)[:500]}...")
            if result.cost:
                print(f"Cost: ${result.cost:.4f}")
        else:
            print(f"Error: {result.error}")
