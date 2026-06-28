---
title: "修改hexo中文章头设置后hexo n报错解决办法"
date: 2023-03-09T11:54:25+08:00
draft: false
tags:
  - hexo
  - 报错
  - 文章新建
typora-root-url: /Users/leesdove/Documents/blog/static
---




这几天利用Github和Hexo搭建个人网页博客，网上这样的教程一堆，但对于我这个小白而言很多看起来很清晰的教程其实里面坑很多，下面就将其中困扰我较长时间的一个问题写出来，以供大家参考。

我是主要参考[weiyang大佬](https://godweiyang.com/2018/04/13/hexo-blog/)的教程搭建的，在网页初步搭建好后，我按照教程，对文章头进行设置，将`/scaffolds/post.md`修改为如下代码：

![](/images/修改hexo中文章头设置后hexo-n报错解决办法/1.png)

结果将原文件进行如上修改后，在git bash里面就频繁报错，

![](/images/修改hexo中文章头设置后hexo-n报错解决办法/2.png)

将故障信息搜索发现，80%以上的都是说没有空格，应添加空格，我之前也遇到过没有添加空格会报：YAMLException: end of the stream or a document separator is expected (2:6)故障

但这个问题，我不论怎样的添加空格都没有用，为此，我郁闷了好久。

后来我想着重新下载matery主题，将原文件和我的文件进行比对看看，终于发现了原来原文件是没有上下三个“---”的，将其去掉后，故障消失，问题得以解决。

![](/images/修改hexo中文章头设置后hexo-n报错解决办法/3.png)

我就是按照如上设置的，目前暂未发现其他问题，希望对后来者有帮助！
