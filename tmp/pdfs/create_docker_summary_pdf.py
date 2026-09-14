from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT = "output/pdf/coursemind_dockerization_summary.pdf"
FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"
BOLD_FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

pdfmetrics.registerFont(TTFont("STHeitiLight", FONT_PATH))
pdfmetrics.registerFont(TTFont("STHeitiMedium", BOLD_FONT_PATH))

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleCn",
        parent=styles["Title"],
        fontName="STHeitiMedium",
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="SubCn",
        parent=styles["BodyText"],
        fontName="STHeitiLight",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="HeadingCn",
        parent=styles["Heading2"],
        fontName="STHeitiMedium",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=4,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCn",
        parent=styles["BodyText"],
        fontName="STHeitiLight",
        fontSize=9.2,
        leading=13,
        textColor=colors.HexColor("#1f2937"),
    )
)
styles.add(
    ParagraphStyle(
        name="IntroCn",
        parent=styles["BodyText"],
        fontName="STHeitiLight",
        fontSize=8.7,
        leading=11.6,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="MiniHeadingCn",
        parent=styles["Heading3"],
        fontName="STHeitiMedium",
        fontSize=9.4,
        leading=11.5,
        textColor=colors.HexColor("#111827"),
        spaceBefore=2,
        spaceAfter=1,
    )
)
styles.add(
    ParagraphStyle(
        name="HeaderCn",
        parent=styles["BodyText"],
        fontName="STHeitiMedium",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#111827"),
    )
)


def p(text, style="BodyCn"):
    return Paragraph(text, styles[style])


def make_table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eefc")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return table


doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=landscape(A4),
    rightMargin=14 * mm,
    leftMargin=14 * mm,
    topMargin=13 * mm,
    bottomMargin=13 * mm,
)

story = [
    p("CourseMind Docker 化分析", "TitleCn"),
    p(
        "这份 PDF 用表格整理 CourseMind 哪些内容适合 Docker 化、哪些不需要单独 Docker 化，以及 Docker 化后相对原先本地启动方式的优势和劣势。",
        "SubCn",
    ),
    p("基础概念", "HeadingCn"),
    p(
        "Docker 可以理解成一个应用运行盒子。这个盒子里可以放运行环境、编程语言运行时、项目依赖、启动命令和某个具体服务。这样别人拿到同一个 Docker 镜像后，就能在相对一致的环境里运行应用，减少“我电脑能跑、你电脑不能跑”的问题。",
        "IntroCn",
    ),
    p(
        "Docker 化，就是把一个服务整理成可以用 Docker 运行的形式。通常会为服务写 Dockerfile，并在 docker-compose.yml 里描述它如何启动、使用哪些端口、读取哪些环境变量、连接哪些其他服务。",
        "IntroCn",
    ),
    p(
        "“打包进 Docker”通常指把代码、依赖、运行环境和启动方式做成 Docker 镜像；镜像像模板，容器则是根据模板真正跑起来的实例。“装进 Docker”是更口语的说法，可能指把某个服务放进容器运行，也可能指在构建镜像时把依赖安装进去。",
        "IntroCn",
    ),
    p("文字讲解", "HeadingCn"),
    p(
        "在 CourseMind 里，可以 Docker 化的内容主要分成三类：已经 Docker 化的基础服务、适合继续 Docker 化的运行模块，以及不太需要单独 Docker 化的项目材料。",
        "IntroCn",
    ),
    p("1. 数据库", "MiniHeadingCn"),
    p(
        "数据库已经 Docker 化。当前 docker-compose.yml 里定义的是 PostgreSQL 17 + pgvector，也就是 CourseMind 的数据库服务已经放在 Docker 容器中运行。",
        "IntroCn",
    ),
    p("2. 后端", "MiniHeadingCn"),
    p(
        "后端很适合 Docker 化。后端镜像可以包含 Python 版本、FastAPI 后端代码、Python 依赖、Uvicorn 启动命令和环境变量读取方式。这样就不用每次手动进入 backend、激活虚拟环境、安装依赖并启动 Uvicorn，而是可以通过 docker compose up backend 启动。",
        "IntroCn",
    ),
    p("3. 前端", "MiniHeadingCn"),
    p(
        "前端也可以 Docker 化。开发阶段可以把 Node.js、npm 依赖、Vite dev server 和 Vue 前端代码放进容器；生产阶段通常先用 Node 构建前端，再用 Nginx 或其他静态服务器托管 dist 文件。",
        "IntroCn",
    ),
    p("4. 数据库迁移", "MiniHeadingCn"),
    p(
        "Alembic 迁移也可以纳入 Docker 流程。它不是一个长期运行的服务，而是一次性任务，例如 docker compose run backend alembic upgrade head，用来把数据库表结构升级到最新。",
        "IntroCn",
    ),
    p("5. 文档上传文件存储", "MiniHeadingCn"),
    p(
        "文档上传文件存储不是服务，但和 Docker 有关系。CourseMind 上传文件目前在 backend/data/uploads；如果后端 Docker 化，这个目录需要挂载成 Docker volume，否则容器重建后上传文件可能丢失。",
        "IntroCn",
    ),
    p("6. 测试环境", "MiniHeadingCn"),
    p(
        "测试环境也适合 Docker 化，例如后端测试容器和测试专用 PostgreSQL + pgvector 容器。这样每次测试都有一致环境，不容易被本机环境影响。",
        "IntroCn",
    ),
    p("分类总结", "MiniHeadingCn"),
    p(
        "已经 Docker 化的是 PostgreSQL + pgvector 数据库；适合 Docker 化的是 FastAPI 后端、Vue/Vite 前端、Alembic 数据库迁移任务、上传文件存储 volume 和测试环境；不太需要单独 Docker 化的是普通源码文件、README、文档和 Alembic 迁移文件本身。更直观地说，能运行、能存数据、依赖环境明显的东西，都适合 Docker 化。",
        "IntroCn",
    ),
    PageBreak(),
    p("1. 内容是否适合 Docker 化", "HeadingCn"),
]

fit_rows = [
    [
        p("内容", "HeaderCn"),
        p("是否适合 Docker 化", "HeaderCn"),
        p("Docker 化后优势", "HeaderCn"),
        p("Docker 化后劣势 / 注意点", "HeaderCn"),
    ],
    [
        p("数据库：PostgreSQL 17 + pgvector"),
        p("已经适合，且当前已经 Docker 化"),
        p("数据库版本、pgvector 扩展、端口和数据卷都更稳定；不需要在本机直接安装 PostgreSQL。"),
        p("必须保护 volume；如果误删数据卷，数据库数据会丢失。"),
    ],
    [
        p("后端：FastAPI / Python / Uvicorn"),
        p("适合"),
        p("Python 版本和依赖固定；不用每次手动进入虚拟环境、安装依赖、启动后端；方便新成员启动。"),
        p("需要写 Dockerfile，处理环境变量、容器网络、热更新和日志查看。"),
    ],
    [
        p("前端：Vue / Vite / Node.js"),
        p("适合"),
        p("Node.js 和 npm 依赖固定；可和后端、数据库一起用 docker compose up 启动。生产环境还能只发布打包后的静态文件。"),
        p("开发热更新需要正确挂载代码目录；生产镜像和开发镜像可能需要分开设计。"),
    ],
    [
        p("数据库迁移：Alembic upgrade"),
        p("适合做成一次性任务"),
        p("迁移命令可以在同一套后端环境里执行，减少本机 Python 环境差异造成的问题。"),
        p("它不是长期服务；要注意执行顺序，通常需要等数据库健康后再运行。"),
    ],
    [
        p("上传文件存储：backend/data/uploads"),
        p("适合用 volume 管理，不是单独容器"),
        p("后端容器重建后，上传文件仍能保留；文件和代码生命周期分开。"),
        p("volume 挂载路径必须配对，否则文件可能写进容器内部，重建后丢失。"),
    ],
    [
        p("测试环境"),
        p("适合"),
        p("可以固定测试依赖和测试数据库，避免本机环境影响测试结果。"),
        p("启动较慢，占用资源更多；需要维护测试专用配置。"),
    ],
    [
        p("普通源码文件"),
        p("不需要单独 Docker 化"),
        p("源码会随前端或后端镜像进入容器，不需要为每个源码目录建容器。"),
        p("如果把源码复制进镜像，修改后通常要重新构建；开发阶段可用挂载解决。"),
    ],
    [
        p("README、开发文档、项目企划书"),
        p("不需要单独 Docker 化"),
        p("继续作为仓库文件保存即可，便于阅读和维护。"),
        p("它们不运行服务，单独容器化没有实际收益。"),
    ],
    [
        p("知识库测试 PDF"),
        p("不需要单独 Docker 化"),
        p("作为测试输入资料保留在仓库或挂载目录中即可。"),
        p("如果文件很大，不宜复制进生产镜像，可考虑挂载或外部存储。"),
    ],
]
story.append(make_table(fit_rows, [41 * mm, 42 * mm, 87 * mm, 85 * mm]))
story.append(Spacer(1, 9))
story.append(p("2. Docker 化前后对比", "HeadingCn"))

compare_rows = [
    [p("对比项", "HeaderCn"), p("Docker 化前", "HeaderCn"), p("Docker 化后", "HeaderCn"), p("总体影响", "HeaderCn")],
    [p("启动方式"), p("通常要分别启动数据库、后端、前端。"), p("可以用 docker compose up 一次拉起整组服务。"), p("启动更统一，日常操作更省心。")],
    [p("环境一致性"), p("依赖本机 Python、Node.js、数据库安装和包版本。"), p("镜像固定运行环境和依赖版本。"), p("更稳定，更适合协作。")],
    [p("调试体验"), p("本机直接看进程、改代码、跑命令。"), p("需要进入容器或查看容器日志。"), p("多一层容器概念，初期会更绕。")],
    [p("资源占用"), p("只运行本机进程和数据库。"), p("容器和镜像会额外占用内存、磁盘和启动时间。"), p("机器配置较低时感受更明显。")],
    [p("数据持久化"), p("数据库和上传文件通常直接落在本机目录或本机服务里。"), p("数据库和上传文件需要 volume 保存。"), p("边界更清楚，但配置错误时有丢数据风险。")],
    [p("部署迁移"), p("换机器时要重新安装环境和依赖。"), p("镜像和 compose 配置可以复用。"), p("更接近真实部署方式。")],
]
story.append(make_table(compare_rows, [38 * mm, 69 * mm, 75 * mm, 73 * mm]))
story.append(Spacer(1, 9))
story.append(p("结论", "HeadingCn"))
story.append(
    p(
        "CourseMind 最适合优先 Docker 化的是后端和前端，并保留当前已经 Docker 化的 PostgreSQL + pgvector 数据库。迁移任务适合纳入 Docker Compose 流程，上传文件应通过 volume 持久化。源码、说明文档和测试 PDF 通常不需要单独 Docker 化。"
    )
)

doc.build(story)
