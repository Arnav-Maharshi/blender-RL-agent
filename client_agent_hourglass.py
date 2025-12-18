import gymnasium as gym
from gymnasium import spaces
import numpy as np
import socket
import json
from stable_baselines3 import PPO
import random

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
        reward -= min((distance*0.2), 2.5)

        if  abs(curr_top_area - dynamic_top_area) < 0.2:
            reward += 3.0
        else:
            reward -= min(abs(curr_top_area - dynamic_top_area)*0.2, 1.5)
        
        terminated = False
        if distance < 0.2 and alignment > 0.9:
            reward += 200 # BIG BONUS
            terminated = True
            print(f"SUCCESS! Target Height {self.target_height:.2f} \n\r\r\r\r\r\r\r\r Reached Height {curr_height:.2f}")
        
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
        
# --- TRAINING ---
if __name__ == "__main__":
    env = RemoteBlenderEnv()
    log_dir = "tensorboard_logs/" # Create a folder for logs
    run_name = "Run_11_HOURGLASS"

    print("Training...")
    model = PPO("MlpPolicy", 
                env, 
                verbose=1,
                tensorboard_log=log_dir,
                n_steps=512,
                ent_coef=0.01,
                device="cpu",
                )
    #model = PPO.load("models/Run_10_HOURGLASS_1.zip", env=env, device="cpu")
    model.learn(total_timesteps=100000, tb_log_name=f"{run_name}", reset_num_timesteps=False)
    
    print("Done! Saving...")
    model.save(f"models/{run_name}_1(100k)")  