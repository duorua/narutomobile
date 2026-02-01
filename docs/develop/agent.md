# Custom 编写

## Agent Server 编写

当需要采用 Pipeline 无法承载的复杂逻辑时，可以在 Agent 注册并托管自定义识别/动作模块。本项目的agent server与`M9A`的agent server类似，均由`Python`编写，所以也适用于`M9A`的[Custom 编写指南](https://1999.fan/zh_cn/develop/custom.html)。

其他参考资料：  
[继承接口一览](https://maafw.com/docs/2.2-IntegratedInterfaceOverview)  
[python接口源码](https://github.com/MaaXYZ/MaaFramework/tree/main/source/binding/Python/maa)  

## Agent Server 打包

> [!ERROR]
> 本项目的agent server打包逻辑已经经过重写。与`M9A`的并不相同！请不要用`M9A`的 agent 打包文档进行参考。具体实现以实际源码为准！
