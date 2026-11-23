import json, math

class XGBLite:
    def __init__(self, path):
        m = json.load(open(path))["learner"]
        bs = float(str(m["learner_model_param"]["base_score"]).strip("[]"))
        self.base = math.log(bs / (1 - bs))
        self.trees = m["gradient_booster"]["model"]["trees"]

    def predict(self, x):
        s = self.base
        for t in self.trees:
            L, R = t["left_children"], t["right_children"]
            n = 0
            while L[n] != -1:
                f = t["split_indices"][n]
                n = L[n] if x[f] < t["split_conditions"][n] else R[n]
            s += t["split_conditions"][n]
        return 1 / (1 + math.exp(-s))
