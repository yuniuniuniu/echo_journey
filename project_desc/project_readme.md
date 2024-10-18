# 以bot为核心驱动的Service
### 1、两个service分别对应瓜瓜和斗斗【talk_practise_service为瓜瓜，负责教学，exercise_service 为 斗斗， 负责训练】
### 2、talk_practise_service 由 三个 bot组成：SceneGenerateBot负责制定教学计划，CorrectBot用来纠音 ，TalkPractiseBot 负责控制总体流程，bot之间如有需要，历史消息共享
### 3、exercise_service 由 三个 bot 组成：1、CorrectBot负责纠音 2、HistoryLearnSituationBot负责对历史学情进行分析 3、ExerciseBot负责练习主流程的推进，bot之间如有需要，历史消息共享

# 代码架构
### echo_journey/api 中代码为接收消息后处理的相关代码，整体链路从这里开始
### echo_journey/services 中包含了所有业务逻辑
### echo_journey/services/bots 中包含了所有bot具体逻辑
### echo_journey/data/whole_context.py 为核心类，抽象单Assistant类Bot 依赖的非逻辑核心内容
### echo_journey/data/orchestrator.py为核心类，抽象多Assistant类Bot 并发协作 依赖的核心内容 包括 节点【bot】边 【如何跳转】历史消息管理、消息预处理等

# 工具链
## 标准的python项目部署、包管理、clean code