---
title: "修改hexo中文章头设置后hexo n报错解决办法"
date: 2023-03-09T11:54:25+08:00
draft: false
tags:
  - hexo
  - 报错
  - 文章新建
---




这几天利用Github和Hexo搭建个人网页博客，网上这样的教程一堆，但对于我这个小白而言很多看起来很清晰的教程其实里面坑很多，下面就将其中困扰我较长时间的一个问题写出来，以供大家参考。

我是主要参考[weiyang大佬](https://godweiyang.com/2018/04/13/hexo-blog/)的教程搭建的，在网页初步搭建好后，我按照教程，对文章头进行设置，将`/scaffolds/post.md`修改为如下代码：

![](/images/%E4%BF%AE%E6%94%B9hexo%E4%B8%AD%E6%96%87%E7%AB%A0%E5%A4%B4%E8%AE%BE%E7%BD%AE%E5%90%8Ehexo-n%E6%8A%A5%E9%94%99%E8%A7%A3%E5%86%B3%E5%8A%9E%E6%B3%95/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20230309140406.png)

结果将原文件进行如上修改后，在git bash里面就频繁报错，

![](/images/%E4%BF%AE%E6%94%B9hexo%E4%B8%AD%E6%96%87%E7%AB%A0%E5%A4%B4%E8%AE%BE%E7%BD%AE%E5%90%8Ehexo-n%E6%8A%A5%E9%94%99%E8%A7%A3%E5%86%B3%E5%8A%9E%E6%B3%95/code.png)

将故障信息搜索发现，80%以上的都是说没有空格，应添加空格，我之前也遇到过没有添加空格会报：YAMLException: end of the stream or a document separator is expected (2:6)故障

但这个问题，我不论怎样的添加空格都没有用，为此，我郁闷了好久。

后来我想着重新下载matery主题，将原文件和我的文件进行比对看看，终于发现了原来原文件是没有上下三个“---”的，将其去掉后，故障消失，问题得以解决。

![](/images/%E4%BF%AE%E6%94%B9hexo%E4%B8%AD%E6%96%87%E7%AB%A0%E5%A4%B4%E8%AE%BE%E7%BD%AE%E5%90%8Ehexo-n%E6%8A%A5%E9%94%99%E8%A7%A3%E5%86%B3%E5%8A%9E%E6%B3%95/code1.png)

我就是按照如上设置的，目前暂未发现其他问题，希望对后来者有帮助！
