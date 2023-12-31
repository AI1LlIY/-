"""
The collision engine of the game.
"""
import pygame as pg
from pygame.math import Vector2

from xcape.common.loader import SFX_RESOURCES
from xcape.common.object import GameObject
from xcape.components.audio import AudioComponent


class CollisionEngine(GameObject):
    """
    A specialised (non-scalable) collision engine that handles collisions
    between all entities in a scene.
    """

    def __init__(self, scene):
        """
        :param scene: Scene Class, representing a level.
        """
        self.scene = scene
        self.audio = AudioComponent(self, isAutoPlay=False)
        self.audio.add("explosion", SFX_RESOURCES["cat_coop_jump"])

    def __str__(self):
        return "collision_engine"

    def eventHandler(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:
                self.resolveDoorCollisions()

            try:
                p1, p2 = self.scene.players
                p1Jump = p1.keybinds["coop_jump"]
                p2Jump = p2.keybinds["coop_jump"]
                if event.key == p1Jump or event.key == p2Jump:
                    self.resolvePlayerCollisions(30)
                    self.audio.state = "explosion"
            except ValueError:
                pass

    def update(self):
        self.resolveWallCollisions()
        self.resolveSwitchCollisions()

        self.resolveSPlatformCollisions()
        self.resolveDPlatformCollisions()
        self.resolveMPlatformCollisions()

        self.resolveSpikeCollisions()
        self.resolveBossCollisions()
        self.resolveBoundaryCollision()

        self.audio.update()

    def resolvePlayerCollisions(self, explosionSpeed):
        """
        Resolves any collisions between players.

        :param explosionSpeed: Integer, the speed at which both players fly
        away from each other in the x-axis and y-axis respectively.
        """
        try:
            p1, p2 = self.scene.players
            if pg.sprite.collide_rect(p1, p2):
                p1.physics.addVelocityY("collision", -explosionSpeed)
                p2.physics.addVelocityY("collision", -explosionSpeed)

                if p2.rect.x > p1.rect.x:
                    p1.physics.addVelocityX("collision", -explosionSpeed)
                    p2.physics.addVelocityX("collision", explosionSpeed)

                else:
                    p1.physics.addVelocityX("collision", explosionSpeed)
                    p2.physics.addVelocityX("collision", -explosionSpeed)

        except ValueError:
            pass

    def resolveWallCollisions(self):
        """
        Resolves any wall collisions.
        """
        for player in self.scene.players:
            self._resolveBasicCollision(player, self.scene.walls)

    def resolveSPlatformCollisions(self):
        """
        Resolves any static platform collisions.
        """
        for player in self.scene.players:
            self._resolveBasicCollision(player, self.scene.sPlatforms)

    def resolveDPlatformCollisions(self):
        """
        Resolves any directional platform collisions.
        """
        for player in self.scene.players:

            hits = pg.sprite.spritecollide(player, self.scene.dPlatforms, False)
            for platform in hits:
                direction = self._checkCollisionDirection(player, platform)

                if direction == "bottom":
                    tol = abs(player.rect.bottom - platform.rect.top)
                    if tol < 30:
                        player.rect.bottom = platform.rect.top
                        player.isOnGround = True

                        # Allows conversation of velocity if the player jumps through
                        if player.physics.velocity.y > 0:
                            player.physics.velocity.y = 0

    def resolveMPlatformCollisions(self):
        """
        Resolves any moving platform collisions.
        """
        for player in self.scene.players:
            hits = pg.sprite.spritecollide(player, self.scene.mPlatforms, False)
            self._resolveBasicCollision(player, self.scene.mPlatforms)

            for platform in hits:
                player.physics.addDisplacementX("platform", platform.dx)
                player.physics.addDisplacementY("platform", platform.dy)

    def resolveSwitchCollisions(self):
        """
        Resolves any switch collisions.
        """
        switchesOn = [s for s in self.scene.switches if s.isOn]
        for s in switchesOn:

            for player in self.scene.players:
                if pg.sprite.collide_rect(player, s):
                    if (player.physics.velocity.x != 0 or
                            player.physics.velocity.y != 0):
                        s.turnOff()

    def resolveDoorCollisions(self):
        """
        Resolves any door collisions.
        """
        for player in self.scene.players:

            hits = pg.sprite.spritecollide(player, self.scene.doors, False)
            doorsClosed = [d for d in self.scene.doors if d.isClosed]
            if hits and not doorsClosed:
                self.messageScene("complete")

    def resolveSpikeCollisions(self):
        """
        Resolves any spike collisions.
        """
        for player in self.scene.players:

            hits = pg.sprite.spritecollide(player, self.scene.spikes, False)
            if hits:
                self.messageScene("death", player.num)

    def resolveBossCollisions(self):
        """
        Resolves any boss collisions.
        """
        for player in self.scene.players:

            hits = pg.sprite.spritecollide(player, self.scene.bosses, False)
            if hits:
                self.messageScene("death", player.num)

    def resolveBoundaryCollision(self):
        """
        Checks if the players have 'fallen' out of the level.
        """
        w, h = self.scene.rect.size
        boundary = pg.Rect(-1000, -1000, w+2000, h+2000)

        for player in self.scene.players:
            if not pg.Rect.contains(boundary, player):
                self.messageScene("death", player.num)

    def _resolveBasicCollision(self, moving, group):
        """
        Resolves any collisions between a moving object and a group of
        objects such that the moving object cannot pass through such objects.

        :param moving: GameObject instance, representing a moving scene entity.
        :param group: List, containing GameObject instance in a scene.
        :return:
        """
        hits = pg.sprite.spritecollide(moving, group, False)

        for wall in hits:
            direction = self._checkCollisionDirection(moving, wall)

            if direction == "bottom":
                moving.rect.bottom = wall.rect.top
                moving.physics.velocity.y = 0
                moving.isOnGround = True

            elif direction == "left":
                moving.rect.left = wall.rect.right
                moving.physics.velocity.x = 0

            elif direction == "top":
                moving.rect.top = wall.rect.bottom
                moving.physics.velocity.y = 0

            elif direction == "right":
                moving.rect.right = wall.rect.left
                moving.physics.velocity.x = 0

    def _checkCollisionDirection(self, moving, static):
        """
        Checks if the moving game object has collided with the static game
        object, and determines the direciton of collision.

        :param moving: GameObject instance, representing a moving game object.
        :param static: GameObject instance, representing a static game object.
        :return: String, whether 'bottom', 'left', 'top', or 'right'.
        """
        if pg.sprite.collide_rect(moving, static):
            x, y = static.rect.center
            S00 = static.rect.topleft
            S10 = static.rect.topright
            S11 = static.rect.bottomright
            S01 = static.rect.bottomleft

           
            u, v = moving.rect.center
            M00 = moving.rect.topleft
            M10 = moving.rect.topright
            M11 = moving.rect.bottomright
            M01 = moving.rect.bottomleft

            vec_M00 = Vector2(x - S00[0], y - S00[1])
            vec_M10 = Vector2(x - S10[0], y - S10[1])
            vec_M11 = Vector2(x - S11[0], y - S11[1])
            vec_M01 = Vector2(x - S01[0], y - S01[1])

           
            FULL_ROTATION = 360
            origin = vec_M00

           
            angle_00 = origin.angle_to(vec_M00) % FULL_ROTATION
            angle_10 = origin.angle_to(vec_M10) % FULL_ROTATION
            angle_11 = origin.angle_to(vec_M11) % FULL_ROTATION
            angle_01 = origin.angle_to(vec_M01) % FULL_ROTATION

           
            displacement = Vector2(x - u, y - v)
            angle = origin.angle_to(displacement) % FULL_ROTATION

            isCollideBottom = angle_00 < angle < angle_10
            isCollideLeft = angle_10 < angle < angle_11
            isCollideTop = angle_11 < angle < angle_01
            isCollideRight = angle_01 < angle

            if isCollideBottom:
                return "bottom"
            elif isCollideLeft:
                return "left"
            elif isCollideTop:
                return "top"
            elif isCollideRight:
                return "right"
