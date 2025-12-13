import gymnasium as gym
from gymnasium import spaces
import numpy as np
import socket
import json
from stable_baselines3 import PPO

class RemoteBlenderEnv(gym.Env):
    def __init__(self):
        super(RemoteBlenderEnv, self).__init__()

        # Connect to Blender
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('localhost', 9999))
       
       # Environment setup
        self.action_space = spaces.Discrete(8)
        
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(7,), # width, depth, height, top_area, normal.x, normal.y, normal.z (of active face)
            dtype=np.float32
        )

        self.target_height = 4.0
        self.target_face = [0,0,1] # Face with normal vector pointing up (top face)

        self.max_steps = 20
        self.current_step = 0

    def _send_command(self, cmd, action=None):
        payload = {"command": cmd}
        if action is not None:
            payload["action"] = int(action)

        self.sock.send(json.dumps(payload).encode()) # converts payload -> JSON string -> bytes and sends it to blender_server.py
        data = self.sock.recv(4096).decode() # recieving up to 4096 bytes from blender_server and then converting data from bytes to string
        return np.array(json.loads(data), dtype=np.float32) # converting data (in JSON string format) -> bytes and sends it to blender_server.py

    def step(self, action):
        self.current_step += 1
        

        observation = self._send_command("STEP", action) # ask blender to move/execute action and return new observation
        curr_height = observation[2]
        curr_normal = observation[4:7]
        reward = 0.0

        alignment = np.dot(np.array(curr_normal), np.array(self.target_face))

        if alignment > 0.9:
            reward += 2.0
        else:
            reward -= 1.0

        distance = abs(self.target_height - curr_height)
        reward -= (distance*0.1)
        
        terminated = False
        if distance < 0.2 and alignment > 0.9:
            reward += 100 # BIG BONUS
            terminated = True
            print(f"SUCCESS! Reached Height {curr_height:.2f}")
        '''else:
            reward -= distance
            terminated = False'''
            
        truncated = (self.current_step >= self.max_steps)
        
        if self.current_step < 5:
            print(f"DEBUG: Action={action}, Normal={curr_normal}, Reward={reward}")

        return observation, reward, terminated, truncated, {}
   

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        
        # Ask Blender to reset and give us the starting numbers
        obs = self._send_command("RESET")
        return obs, {}
        
# --- TRAINING ---
if __name__ == "__main__":
    env = RemoteBlenderEnv()
    
    print("Training...")
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=1000)
    
    print("Done! Saving...")
    model.save("my_remote_agent")  