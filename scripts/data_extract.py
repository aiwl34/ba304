from datasets import load_dataset

ds = load_dataset("NbAiLab/norwegian-alpaca")
ds = ds["train"]

ds = ds.remove_columns(["instruction_en", "input_en", "output_en"])
ds = ds.filter(lambda x: x["input"] is not None and x["input"] != "")
ds = ds.shuffle(seed=42).select(range(350))

df = ds.to_pandas()
df.to_json("../input_data/dataset.json", orient="records", force_ascii=False, indent=2)