# Filename: marl_pde_vs_agentbased.py
# 完整实现：Agent-based Q-learning + PDE（m=2 情形）
# 作者：ChatGPT（示例代码），用途：教学/实验
# 运行：python marl_pde_vs_agentbased.py
# 依赖：numpy, matplotlib

import numpy as np
import matplotlib.pyplot as plt
from math import factorial
import random

# --------------------------- 配置（可修改） ---------------------------
np.random.seed(0)
random.seed(0)

# 博弈矩阵（示例：论文中的 Prisoner's Dilemma）
R_PD = np.array([[1.0, 0.0],
                 [1.5, 0.0]])
games = {'PD': R_PD}

# 学习与数值参数（可根据需要调整）
beta = 2.0       # Boltzmann 温度（公式 1）
alpha = 0.4      # 学习率（公式 2）
k = 4            # 每个智能体的邻居数（规则图度）
T_steps = 80     # 模拟时间步数（Agent 与 PDE 的时间步数量）
dt = 0.1         # PDE 时间步长（显式欧拉）
grid_n = 41      # PDE 网格密度（每轴点数）
N_agents = 2000  # Agent-based 仿真中智能体数量（越大越接近 PDE 假设）

# --------------------------- 工具函数 ---------------------------
def softmax_prob(Qvec, beta):
    """
    稳定的 Boltzmann (softmax) 计算：输入为一维 Qvec（长度 m=2）
    返回各动作概率（和为1）
    注意：为数值稳定性可做减 max 操作（此处简单实现）
    """
    shift = np.max(beta * Qvec)
    ex = np.exp(beta * Qvec - shift)
    return ex / np.sum(ex)

def multinomial_prob_two_actions(k_counts, xbar):
    """
    计算 m=2 时的多项式（多项分布）概率 f(gamma)
    k_counts: (k1, k2), xbar: (p1, p2)
    返回 f(gamma) = k!/(k1! k2!) * p1^k1 * p2^k2
    """
    k = sum(k_counts)
    k1, k2 = k_counts
    coeff = factorial(k) // (factorial(k1) * factorial(k2))
    return coeff * (xbar[0]**k1) * (xbar[1]**k2)

# --------------------------- Agent-based Q-learning（Algorithm 1） ---------------------------
def agent_based_sim(R, N=N_agents, T=T_steps, k=k):
    """
    Agent-based Q-learning:
    - N agents
    - 每个 agent 保持 Q（长度 m=2）
    - 每步根据 Boltzmann 策略采样动作
    - 每个 agent 随机抽取 k 个邻居（近似规则图）
    - 与每个邻居博弈并平均奖励；更新 Q（只更新被执行动作对应的值）
    返回：
      avg_strategy_history: T x m 的数组（每步群体平均策略）
      Q: 最终 Q 矩阵 N x m
    """
    m = 2
    Q = np.zeros((N, m))  # 初始 Q 全零（可改为随机）
    avg_strategy_history = []

    for t in range(T):
        # 1) 每个 agent 计算 softmax 概率并采样动作
        probs = np.exp(beta * Q)
        probs = probs / probs.sum(axis=1, keepdims=True)  # shape (N,m)
        # 采样动作（每个 agent 一次）
        actions = [np.random.choice(m, p=probs[i]) for i in range(N)]

        # 2) 对每个 agent 随机抽取 k 个邻居并计算平均奖励
        rewards = np.zeros(N)
        for i in range(N):
            ai = actions[i]
            # 随机选择邻居（无自环）；注意：这是近似规则图，如需严格规则图请固定邻接
            neighbors = random.sample([j for j in range(N) if j != i], k)
            r_sum = 0.0
            for j in neighbors:
                aj = actions[j]
                r_sum += R[ai, aj]
            rewards[i] = r_sum / k

        # 3) 更新 Q（只更新所采取动作对应的 Q）
        for i in range(N):
            a = actions[i]
            Q[i, a] = Q[i, a] + alpha * (rewards[i] - Q[i, a])

        # 4) 记录群体平均策略（这里取每个 agent 的 softmax 概率平均）
        avg_prob = probs.mean(axis=0)
        avg_strategy_history.append(avg_prob.copy())

    return np.array(avg_strategy_history), Q

# --------------------------- PDE 数值解（有限差分，m=2） ---------------------------
def pde_solver(R, grid_n=grid_n, T=T_steps, dt=dt, k=k):
    """
    PDE 数值解（基于论文公式(15),(16)的离散化实现，m=2）：
    - 在 Q 空间（Q1, Q2）建立一个 grid_n x grid_n 的网格
    - p(Q,t) 在网格上表示为矩阵 p
    - 时间推进：显式欧拉 p_{t+dt} = p_t + dt * RHS（RHS 根据论文公式离散化）
    返回：
      avg_strategy_history: T x 2 的平均策略随时间演化
      p: 最终的 p(Q) 网格（归一化）
      (q1, q2): 网格坐标一维数组
      (Q1, Q2): 网格二维坐标矩阵
    """
    m = 2
    rmin = float(np.min(R))
    rmax = float(np.max(R))
    # 给网格范围加一点 margin（确保 Q 空间覆盖）
    margin = 0.1 * (rmax - rmin + 1e-8)
    qmin = rmin - margin
    qmax = rmax + margin

    q1 = np.linspace(qmin, qmax, grid_n)
    q2 = np.linspace(qmin, qmax, grid_n)
    dq1 = q1[1] - q1[0]
    dq2 = q2[1] - q2[0]
    Q1, Q2 = np.meshgrid(q1, q2, indexing='ij')

    # 初始 p(Q,0)：小高斯峰（集中在 (0,0)）
    sigma = 0.02 * (qmax - qmin + 1e-8)
    p = np.exp(-((Q1 - 0.0)**2 + (Q2 - 0.0)**2) / (2 * sigma**2))
    p = p / p.sum()

    avg_strategy_history = []
    gamma_list = [(i, k - i) for i in range(k + 1)]  # m=2 的所有 gamma

    for step in range(T):
        # 1) 网格上每点的策略（Boltzmann）
        x1 = np.exp(beta * Q1)
        x2 = np.exp(beta * Q2)
        denom = x1 + x2
        prob_a1 = x1 / denom
        prob_a2 = x2 / denom

        # 2) 计算整体平均策略 \bar{x}（离散积分）
        xbar1 = (p * prob_a1).sum()
        xbar2 = (p * prob_a2).sum()
        xbar = (xbar1, xbar2)
        avg_strategy_history.append(np.array([xbar1, xbar2]))

        # 3) 计算 RHS（对每个 gamma 求和）
        RHS = np.zeros_like(p)
        # f(γ) 对每个 gamma 的值
        f_vals = [multinomial_prob_two_actions(g, xbar) for g in gamma_list]

        # S1 = p * prob_a1, S2 = p * prob_a2
        S1 = p * prob_a1
        S2 = p * prob_a2

        # 计算导数 ∂(p x)/∂Q1 和 ∂(p x)/∂Q2（数值差分）
        dS1_dQ1 = np.zeros_like(S1)
        dS2_dQ2 = np.zeros_like(S2)

        # Q1 方向中心差分（内部），边界用一阶前/后差
        dS1_dQ1[1:-1, :] = (S1[2:, :] - S1[:-2, :]) / (2 * dq1)
        dS1_dQ1[0, :] = (S1[1, :] - S1[0, :]) / dq1
        dS1_dQ1[-1, :] = (S1[-1, :] - S1[-2, :]) / dq1

        # Q2 方向中心差分（内部），边界用一阶前/后差
        dS2_dQ2[:, 1:-1] = (S2[:, 2:] - S2[:, :-2]) / (2 * dq2)
        dS2_dQ2[:, 0] = (S2[:, 1] - S2[:, 0]) / dq2
        dS2_dQ2[:, -1] = (S2[:, -1] - S2[:, -2]) / dq2

        # 对每个 gamma 贡献进行累加
        for idx_gamma, gamma in enumerate(gamma_list):
            k1_count, k2_count = gamma
            f_g = f_vals[idx_gamma]
            # 计算即时奖励 r(a1|gamma), r(a2|gamma)（公式 (5)-(6) 离散化）
            r_a1 = (1.0 / k) * (k1_count * R[0, 0] + k2_count * R[0, 1])
            r_a2 = (1.0 / k) * (k1_count * R[1, 0] + k2_count * R[1, 1])
            # v_j = alpha * (r - Q_j)
            v1 = alpha * (r_a1 - Q1)
            v2 = alpha * (r_a2 - Q2)
            # RHS 累加： f(γ) * ( v1 * ∂(p x_a1)/∂Q1 + v2 * ∂(p x_a2)/∂Q2 )
            RHS += f_g * (v1 * dS1_dQ1 + v2 * dS2_dQ2)

        # 4) 时间推进（显式欧拉）
        p = p + dt * RHS

        # 保持 p 非负并归一化
        p = np.maximum(p, 0)
        s = p.sum()
        if s <= 0:
            # 若数值退化，重新初始化为小高斯
            p = np.exp(-((Q1 - 0.0)**2 + (Q2 - 0.0)**2) / (2 * sigma**2))
            p = p / p.sum()
        else:
            p = p / s

    return np.array(avg_strategy_history), p, (q1, q2), (Q1, Q2)

# --------------------------- 主程序：运行并绘图 ---------------------------
def main():
    R = games['PD']
    print("开始 Agent-based 仿真...")
    agent_hist, Q_final = agent_based_sim(R, N=N_agents, T=T_steps, k=k)
    print("Agent-based 仿真完成。")

    print("开始 PDE 求解...")
    pde_hist, p_final, (q1, q2), (Q1, Q2) = pde_solver(R, grid_n=grid_n, T=T_steps, dt=dt, k=k)
    print("PDE 求解完成。")

    # 绘制平均策略随时间的对比
    t = np.arange(T_steps)
    plt.figure(figsize=(9,5))
    plt.plot(t, agent_hist[:, 0], label='Agent-based a1 (avg)')
    plt.plot(t, agent_hist[:, 1], label='Agent-based a2 (avg)')
    plt.plot(t, pde_hist[:, 0], '--', label='PDE a1 (avg)')
    plt.plot(t, pde_hist[:, 1], '--', label='PDE a2 (avg)')
    plt.xlabel('Time step')
    plt.ylabel('Average action probability')
    plt.title("Average strategy evolution - Agent-based vs PDE (PD)")
    plt.legend()
    plt.grid(True)
    plt.show()

    # PDE 最终 p(Q) 的热图（Q1-Q2 投影）
    plt.figure(figsize=(6,5))
    plt.contourf(Q1, Q2, p_final, levels=30)
    plt.xlabel('Q(a1)')
    plt.ylabel('Q(a2)')
    plt.title('PDE final p(Q) density (projected)')
    plt.colorbar(label='p(Q)')
    plt.show()

    print("Agent-based final average strategy:", agent_hist[-1])
    print("PDE final average strategy:", pde_hist[-1])

if __name__ == "__main__":
    main()
