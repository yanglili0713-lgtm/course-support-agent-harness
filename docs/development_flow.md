# Development Flow

本项目用于学习 Agent 工程化时的需求拆解顺序。

1. **先画状态机**：把需求拆成稳定阶段，确认每个阶段的输入输出。
2. **再写 Gate**：任何模型输出进入下一阶段前都要校验。
3. **定义数据结构**：用 `schemas.py` 固化 Session、Plan、Gate、Memory、Tool、RAG 类型。
4. **实现子 Agent 隔离**：每个 Agent 只有自己的历史和允许工具。
5. **装配上下文**：不要把所有内容拼成一坨 prompt，要分层。
6. **接入 RAG 和 Skills**：确定性计划走 Skills，外部知识走 RAG。
7. **落盘复盘**：Transcript 比控制台日志更重要，因为它能还原每一步。
8. **最后换模型**：先用 offline mock 跑通机制，再接真实 OpenAI 兼容接口。

