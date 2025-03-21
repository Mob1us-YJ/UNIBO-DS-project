# src/common/models.py
from pygame.math import Vector2
from pygame import Rect

class GameObject:
    def __init__(self, size, position=None, speed=None, name=None):
        self.size = Vector2(size)
        self.position = Vector2(position) if position is not None else Vector2()
        self.speed = Vector2(speed) if speed is not None else Vector2()
        self.name = name or self.__class__.__name__.lower()
    
    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            self.name == other.name and \
            self.size == other.size and \
            self.position == other.position and \
            self.speed == other.speed

    def __hash__(self):
        return hash((type(self), self.name, self.size, self.position, self.speed))

    def __repr__(self):
        return f'<{type(self).__name__}(id={id(self)}, name={self.name}, size={self.size}, position={self.position}, speed={self.speed})>'

    def __str__(self):
        return f'{self.name}#{id(self)}'
    
    @property
    def bounding_box(self):
        return Rect(self.position - self.size / 2, self.size)
    
    def update(self, dt):
        self.position = self.position + self.speed * dt