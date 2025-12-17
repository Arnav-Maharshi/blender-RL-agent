import gymnasium as gym
from gymnasium import spaces
import numpy as np
import socket
import json
from stable_baselines3 import PPO
import random
import time

model_path = f"models/Run_10_HOURGLASS_1(100k).zip"
#model_path = "./my_remote_agent.zip"
episodes = 10000

class RemoteBlenderEnv(gym.Env):
    def __init__(self):
        super(RemoteBlenderEnv, self).__init__()

        # Connect to Blender
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('localhost', 9999))
       
       # Environment setup
        self.action_space = spaces.Discrete(9)
        
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(8,), # width, depth, height, top_area, normal.x, normal.y, normal.z (of active face), target_height
            dtype=np.float32
        )

        self.target_height = random.uniform(2.0, 10.0)
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
        
        observation = np.append(observation, self.target_height) # "reminding" the agent what it's target is
        curr_height = observation[2]
        curr_top_area = observation[3]
        curr_normal = observation[4:7]
        reward = 0.0 # ensuring reward/punishment does not accumulate over steps

        alignment = np.dot(np.array(curr_normal), np.array(self.target_face))

        if alignment > 0.9:
            reward += 2.0
        else:
            reward -= 1.0

        midpoint = self.target_height / 2.0
        dynamic_top_area = 0.1 * (midpoint - curr_height)**2

        distance = abs(self.target_height - curr_height)
        reward -= min((distance*0.2), 1.5)
        
        terminated = False
        if distance < 0.2 and alignment > 0.9 and abs(curr_top_area - dynamic_top_area) < 0.2:
            reward += 200 # BIG BONUS
            terminated = True
            print(f"SUCCESS! Target Height {self.target_height:.2f} \n\r\r\r\r\r\r\r\r Reached Height {curr_height:.2f}")
        reward -= abs(curr_top_area - dynamic_top_area)*0.2
        
        truncated = (self.current_step >= self.max_steps)
        
        '''if self.current_step < 5:
            print(f"DEBUG: Action={action}, Normal={curr_normal}, Reward={reward}")'''

        return observation, reward, terminated, truncated, {}
   

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.target_height = random.uniform(2.0, 10.0)

        # Ask Blender to reset and give us the starting numbers
        obs = self._send_command("RESET")
        obs = np.append(obs, self.target_height) # setting up the new target after each episode

        return obs, {}
        
# --- TESTING ---
if __name__ == "__main__":
    print("Testing...")
    env = RemoteBlenderEnv()
    env.reset()
    model = PPO.load(model_path, env=env, device="cuda")
    
    for ep in range(9950,episodes):
        obs, _ = env.reset()

        # Printing target height and episode count
        target_h = obs[7] 
        print(f"\n--- EPISODE {ep+1} Start. TARGET HEIGHT: {target_h:.2f}m ---")

        done = False
        while not done:
            action, _states = model.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            time.sleep(0.1)  # Slow down for observation
            done = terminated or truncated
        print(f"EPISODE FINISHED. \n Reward: {reward:.2f}\n\n")
        time.sleep(1)  # Pause between episodes