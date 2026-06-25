---
title: "Git学习_删除文件"
date: 2023-03-27T16:44:16+08:00
draft: false
tags:
---


1.如果你用的rm删除文件，那就相当于只删除了工作区的文件，如果想要恢复，直接用git restore  <file>就可以 

2.如果你用的是git rm删除文件，那就相当于不仅删除了文件，而且还添加到了暂存区，需要先git reset HEAD <file>，然后再git restore  <file> 

3.如果你想彻底把版本库的删除掉，先git rm，再git commit 就ok了



