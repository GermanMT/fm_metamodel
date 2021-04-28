import sys

from famapy.core.transformations import TextToModel
from famapy.core.models.ast import AST
from famapy.core.exceptions import DuplicatedFeature
from famapy.metamodels.fm_metamodel.models.feature_model import Feature, FeatureModel, Relation, Constraint


class AFMTransformation(TextToModel):

    @staticmethod
    def get_source_extension() -> str:
        return 'afm'

    def __init__(self, path):
        self.path = path
        self.name_feature = {}
        self.parents = []
        self.ctc_counter = [0,0,0]

    def transform(self):
        with open(self.path, 'r') as lines:
            lines = [line.strip() for line in lines.readlines() if line.strip() != ""]
        for line in lines:
            if line.__contains__("%Relationships"):
                index_r = lines.index(line)
            if line.__contains__("%Constraints"):
                index_c = lines.index(line)
        relations = lines[index_r+1:index_c]
        constraints = lines[index_c+1:]

        fm = FeatureModel(Feature("", []))
        for relation in relations:
            words = relation.split(" ")
            self.parse_features(words, fm)

        for constraint in constraints:
            constraint = constraint.replace(";","")
            ctc = self.parse_ctc(constraint)
            fm.ctcs.append(ctc)

        return fm

    def parse_ctc(self,ctc: str)->Constraint:
        if ctc.__contains__("REQUIRES"):
            self.ctc_counter[0] += 1
            return Constraint("Re-" + str(self.ctc_counter[0]), AST(ctc.replace("REQUIRES","requires")))
        elif ctc.__contains__("EXCLUDES"):
            self.ctc_counter[1] += 1
            return Constraint("Ex-" + str(self.ctc_counter[1]), AST(ctc.replace("EXCLUDES","excludes")))
        elif ctc.__contains__("IMPLIES"):
            features = ctc.split("IMPLIES")
            parts = features[1].split("OR")
            i = 0
            transform = parts[0].replace("(","").replace(")","")
            for part in parts[1:]:
                transform = transform + " or " + "(" + part.replace("(","").replace(")","")
                i += 1
            transform = transform + ")"*i
            transform = transform.replace("AND", "and").replace("NOT", "not")
            self.ctc_counter[2] += 1
            return Constraint("Im-" + str(self.ctc_counter[2]), AST(features[0]+" implies "+transform))

    def parse_features(self, words: list[str], model: FeatureModel) -> Feature:
        name = words[0].replace(":","")
        words.pop(0)

        if name in self.parents:
            print("This AFM contains duplicated feature names", file=sys.stderr)
            raise DuplicatedFeature
        self.parents.append(name)

        feature_parent = Feature(name, [])
        if name in self.name_feature:
            feature_parent = self.name_feature[name]
        else:
            model.features.append(feature_parent)
            model.root = feature_parent
            self.name_feature[name] = feature_parent

        alternative_rel = "[1,1]"
        or_rel = "[1," + str(len(words)-1) + "]"
        if words.__contains__(alternative_rel) or words.__contains__(or_rel):
            if words.__contains__(alternative_rel):
                words.remove(alternative_rel)
                relation = self.parse_relation("Alternative", feature_parent)
            elif words.__contains__(or_rel):
                words.remove(or_rel)
                relation = self.parse_relation("Or", feature_parent, len(words))
            for word in words:
                word = word.replace("{","").replace("}","").replace(";","")
                self.add_feature(relation, word, model)
        else:
            for word in words:
                if word.__contains__("[") and word.__contains__("]"):
                    relation = self.parse_relation("Optional", feature_parent)
                    word = word.replace("[","").replace("]","").replace(";","")
                    self.add_feature(relation, word, model)
                else:
                    relation = self.parse_relation("Mandatory", feature_parent)
                    word = word.replace(";","")
                    self.add_feature(relation, word, model)

        return feature_parent

    def add_feature(self, relation, word, model) -> None:
        if word in self.name_feature:
            print("This AFM contains duplicated feature names", file=sys.stderr)
            raise DuplicatedFeature
        feature = Feature(word, [])
        model.features.append(feature)
        self.name_feature[word] = feature
        relation.children.append(feature)

    def parse_relation(self, type: str, feature_parent: Feature, max=None) -> Relation:
        if type == "Mandatory" or type == "Alternative":
            r = Relation(parent=feature_parent, children=[], card_min=1, card_max=1)
        elif type == "Optional":
            r = Relation(parent=feature_parent, children=[], card_min=0, card_max=1)
        elif type == "Or":
            r = Relation(parent=feature_parent, children=[], card_min=1, card_max=max)
        feature_parent.relations.append(r)
        return r