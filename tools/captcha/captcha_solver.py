from base import AbsstractCaptchaSolver


class RecaptchaSolver(AbsstractCaptchaSolver):
    # RecaptchaSolver use machine learning apis to analyze captcha resilt
    solver_url = ""
    api_key = ""

    async def solve(image_path, target):
        pass
