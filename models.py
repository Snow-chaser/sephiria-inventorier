# models.py
# [클래스 정의]
class Item:
    def __init__(self, name, item_type):
        self.name = name
        self.item_type = item_type


class Tablet(Item):
    def __init__(self, name, directions, turnable=False, constraint=None, tier='common', quant=0):
        super().__init__(name, 'Tablet')
        self.directions = directions
        self.turnable = turnable
        self.constraint = constraint
        self.tier = tier
        self.quant = quant


class Artifact(Item):
    def __init__(self, name, max_level, current_enchant=0, constraint=None, priority=False, combo=None,
                 is_unique=False, is_unit=False, is_spell=False, quant=0):
        super().__init__(name, 'Artifact')
        self.max_level = max_level
        self.current_enchant = current_enchant
        self.priority = priority
        self.is_unique = is_unique
        self.is_unit = is_unit # 동료 소환 여부(헌신의 휘장)
        self.is_spell = is_spell # 마법서 여부(빛나는 모래시계)
        self.quant = quant
        self.scale_position = None  # 대립의 천칭용 (좌측/우측)
        self.apply_devotion = False # 헌신의 휘장 적용 여부
        if not combo:
            self.combo = set()
        elif isinstance(combo, str):
            self.combo = {combo}
        else:
            self.combo = set(combo)

        if constraint is None:
            self.constraint = set()
        elif isinstance(constraint, str):
            self.constraint = {constraint}
        else:
            self.constraint = set(constraint)