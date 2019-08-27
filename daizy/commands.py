import vk_api

class CommandProcessor:
    def __init__(self, vk, peer_id: int):
        self.vk = vk
        self.peer = peer_id

    def identify(self, screen_name):
        x = self.vk.utils.resolveScreenName(screen_name=screen_name)
        self.vk.messages.send(peer_id=self.peer, message=str(x), random_id=vk_api.utils.get_random_id())
