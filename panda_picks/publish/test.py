from panda_picks.publish.twitter import generate_reasoning_template, generate_dick_picks_preview
# path = generate_reasoning_template("WEEK1", overwrite=True)  # overwrite optional
# print(path)
#
# from panda_picks.publish.twitter import generate_dick_picks_preview
# payloads = generate_dick_picks_preview("WEEK1", dest_dir="preview_week1")
# for p in payloads:
#     print(p["text"], p.get("image_paths"))

from panda_picks.publish.twitter import generate_dick_picks_preview
payloads = generate_dick_picks_preview("WEEK1", dest_dir="preview_week1")
for p in payloads:
    print(p["text"], p["image_paths"])