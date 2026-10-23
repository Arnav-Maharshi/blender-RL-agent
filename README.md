# Blender RL Agent: Procedural 3D Mesh Generation

<p align="center">
  <video src="./Project documentation/#5_demo learning to create hourglass (Run_10_1).mp4" width="100%" alt="Blender Agent in Action"></video >
</p>

## Overview
This project features a Reinforcement Learning (RL) agent trained to manipulate a 3D mesh toward a target height and top-face geometry within Blender. By leveraging a custom Gymnasium environment and Proximal Policy Optimization (PPO), the agent learns to autonomously select mesh faces, scale geometry, and extrude regions to sculpt specific 3D shapes.

## Key Features & Architecture
*   **Client-Server Simulation:** Uses socket-based communication to bridge the Python-based RL training script with a local Blender simulation server.
*   **Custom Environment:** Built a dedicated Gymnasium environment that feeds structured geometric observations (width, depth, height, face area, and normal vectors) directly to the agent.
*   **Geometric Reward Shaping:** Engineered a custom reward function that encourages goal-directed mesh growth by rewarding correct face alignment and penalizing height errors.
*   **Model Evaluation:** Includes a complete pipeline for training models, saving checkpoints, and running evaluation episodes to test the agent's success rate.

## Tech Stack
*   **Environment:** Blender 3D
*   **Languages & Frameworks:** Python, Gymnasium, Stable-Baselines3 (PPO), NumPy
*   **Tools:** Local Sockets, TensorBoard (for training metrics)




## Repository structure

- `blender_server.py`: Blender-side server that executes actions and returns geometric observations.
- `client_agent_hourglass.py`: The main script for training the PPO agent on the shape generation task.
- `test_agent_hourglass.py`: The evaluation script for loading and testing saved models.
- `blenderRL.py`: earlier prototype environment and experiments.
- `client_agent.py`: legacy training client.
- `blenderRL_environment.blend`: Blender scene used by the project.
- `models/`: PPO checkpoints.
- `tensorboard_logs/`: training logs.
- `Project documentation/`: supporting outputs and notes.

## Environment

The environment exposes a vector observation with:

- width
- depth
- height
- top face area
- active face normal x/y/z
- target height

Action space:

- `Discrete(9)`

Action mapping:

- 0–5: select face by direction
- 6: scale down
- 7: scale up
- 8: extrude

## Reward design

The reward encourages:

- correct face alignment
- target height progress
- matching a dynamic target area near the midpoint of the target height
- final success when the mesh reaches the intended geometry

It also penalizes height error and poor alignment.

## Viewing TensorBoard logs

The event files in `tensorboard_logs/` can be viewed with TensorBoard. After cloning the repository, open a terminal in the project folder and run:

```powershell
python -m pip install tensorboard
tensorboard --logdir="tensorboard_logs"
```
Then open http://localhost:6006 in a browser. Keep the terminal running while viewing the dashboard; press Ctrl+C to stop it.

This runs TensorBoard on your own computer