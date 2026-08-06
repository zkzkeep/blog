---
title: 群晖 SA6400 RAID 5 硬盘温度查看与排查记录
date: 2026-08-06
tags:
  - 群晖
  - SA6400
  - RAID 5
  - HC550
  - SMART
typora-root-url: /Users/leesdove/Documents/blog/static
---
设备为群晖 SA6400，运行 DSM 7.3，6 块内置 SATA WD Ultrastar HC550 组成 RAID 5。存储空间管理员中只能看到硬盘状态“良好”，未显示温度，因此通过 SSH 核实硬盘实际温度。

## 通过 SSH 读取温度

在 DSM 的“控制面板 → 终端机和 SNMP”启用 SSH 后，登录 NAS，执行：

```bash
sudo synodisk --read_temp /dev/sata1
```

返回示例：

```text
disk /dev/sata1 temp is 41
```

其中数字单位为摄氏度。`/dev/sata1` 到 `/dev/sata6` 分别对应六块物理 SATA 硬盘。

可一次查看全部物理盘：

```bash
for i in {1..6}; do
  sudo synodisk --read_temp /dev/sata$i
done
```

注意：不要对 `/dev/sata1p1`、`/dev/sata1p2` 等分区逐一判断；它们只是同一物理盘上的系统、交换或数据分区，温度与对应物理盘相同。

## 本次温度结果

| 硬盘 | 温度 |
| --- | ---: |
| /dev/sata1 | 41°C |
| /dev/sata2 | 39°C |
| /dev/sata3 | 38°C |
| /dev/sata4 | 39°C |
| /dev/sata5 | 41°C |
| /dev/sata6 | 38°C |

六块盘温度在 38–41°C 之间，最大差值仅 3°C。对 7200 RPM 的企业级 HC550 而言，这个温度区间正常，且说明 SA6400 的盘位风道和散热较均匀。

## 温度参考

- 30–45°C：正常。
- 46–50°C：仍可接受，建议关注机柜与机箱通风。
- 持续超过 50°C：检查灰尘、进出风、环境温度，并考虑提高风扇速度模式。
- 55°C 以上：应尽快处理散热问题。

## 结论

本机硬盘温度可以被 DSM 的底层磁盘工具正常读取；存储空间管理员只展示“良好”，更可能是 DSM 7.3 的界面展示差异，并不表示 HC550、SATA 连接或 RAID 5 存在故障。当前无需调整风扇或进行硬盘操作。
