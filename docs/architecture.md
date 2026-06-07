# Architecture

## 七层 Harness

1. **Control Plane**：状态机与 Gate。它决定 PLAN、EXECUTE、VERIFY、CONSOLIDATE、DONE、HALT 的流转。
2. **Memory**：四层记忆，避免所有历史都塞进 prompt。
3. **Context**：七段式上下文装配，隔离稳定前缀和易变任务输入。
4. **Sub-Agent**：Examiner 和 Grader 独立实例、独立历史、显式传参。
5. **RAG**：检索证据进入上下文，不让模型凭空出题或评分。
6. **Skills**：确定性生成 Session Plan，减少模型自由发挥。
7. **MCP**：工具网关控制权限、执行和审计。

## 为什么 LLM 不控制流程

模型输出不稳定，不能承担“是否继续、是否重试、是否停止”的最终决策。Harness 用 Gate 把模型输出变成可验证事件：

- 出题必须非空、足够长、像问题。
- 评分必须包含 0-100 的 score。
- 工具调用必须通过白名单。
- Replan 有上限，超过后受控 HALT。

