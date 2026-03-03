from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class MatchStats(BaseModel):
    touches: int
    completed_passes: int
    failed_passes: int
    positive_actions: int
    negative_actions: int


@app.get("/")
def root():
    return {"message": "ProScout API is running"}


@app.post("/analyze")
def analyze(stats: MatchStats):

    total_passes = stats.completed_passes + stats.failed_passes

    pass_accuracy = 0
    if total_passes > 0:
        pass_accuracy = (stats.completed_passes / total_passes) * 100 

    # ציון פשוט לגרסה ראשונה
    score = (
        stats.touches * 0.1 +
        pass_accuracy * 0.05 +
        stats.positive_actions * 0.5 -
        stats.negative_actions * 0.5
    )

    # הגבלה ל 0–10
    final_score = max(0, min(10, round(score, 2)))

    return {
        "touches": stats.touches,
        "pass_accuracy": round(pass_accuracy, 2),
        "positive_actions": stats.positive_actions,
        "negative_actions": stats.negative_actions,
        "final_score": final_score
    }
