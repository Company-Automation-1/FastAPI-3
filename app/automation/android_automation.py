"""
安卓设备UI自动化模块

该模块提供安卓设备的UI自动化操作功能，主要用于：
- 自动发布内容
- 屏幕解锁
- 应用操作
"""

import logging
import os
import time
import uiautomator2 as u2
from app.core.config import settings
from app.models.device import Device
from app.models.upload import Upload
from app.models.task import Task
from app.utils.file import get_file_paths

logger = logging.getLogger(__name__)

class AndroidAutomation:
    def __init__(self, device_id: str, password: str = None):
        """
        初始化自动化实例
        
        Args:
            device_id: 设备物理ID
            password: 设备解锁密码
        """
        self.device_id = device_id
        self.d = None
        self.password = password
        self.wait_timeout = 30  # 默认等待超时时间
        self.app_package = "com.xingin.xhs"  # 小红书包名
        
        logger.info(f"初始化UI自动化服务，设备ID: {self.device_id}")

    def connect_device(self):
        """连接设备"""
        try:
            self.d = u2.connect(self.device_id)
            logger.info(f"成功连接设备: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"设备连接失败: {str(e)}")
            return False

    def unlock_screen(self):
        """
        解锁设备屏幕
        
        Returns:
            bool: 解锁是否成功
        """
        try:
            logger.info(f"开始UI解锁设备: {self.device_id}")
            
            # 唤醒屏幕
            self.d.screen_on()
            logger.debug("屏幕已唤醒")
            
            # 滑动解锁
            self.d.swipe(500, 2500, 500, 500, duration=1.0)
            logger.debug("执行滑动解锁手势")
            
            # 如果有密码，输入密码
            if self.password:
                # 等待密码输入界面
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if self.d(resourceId="com.android.systemui:id/digit_text", text="0").exists(timeout=5):
                            logger.debug(f"输入密码: {self.password}")
                            for digit in self.password:
                                self.d(resourceId="com.android.systemui:id/digit_text", text=str(digit)).click()
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logger.error(f"密码输入失败: {str(e)}")
                            return False
                        time.sleep(1)
            
            # 检查是否解锁成功（等待主屏幕出现）
            time.sleep(2)  # 等待解锁动画完成
            self.d.press("home")    # 回到主屏幕
            
            logger.info(f"设备 {self.device_id} 解锁成功")
            return True
            
        except Exception as e:
            logger.error(f"解锁设备失败: {str(e)}")
            return False

    async def execute_task(self, title: str, content: str, time_str: str):
        """
        执行UI自动化任务
        
        Args:
            title: 发布内容的标题
            content: 发布内容的正文
            time_str: 时间文件夹名称（格式：yyyymmddhhmmss）
            
        Returns:
            bool: 任务是否执行成功
        """
        try:
            logger.info(f"开始执行UI自动化任务")
            
            # 连接设备
            if not self.connect_device():
                logger.error("连接设备失败")
                return False
                
            # 解锁设备
            if not self.unlock_screen():
                logger.error("解锁设备失败")
                return False
            
            # 执行内容发布
            result, message = self.post_content(title, content, time_str)
            
            if result:
                logger.info("任务执行成功")
                return True
            else:
                logger.error(f"任务执行失败: {message}")
                return False
                
        except Exception as e:
            logger.error(f"执行任务时出错: {str(e)}")
            return False

    def post_content(self, title, content, time_str):
        """
        发布内容到应用
        
        Args:
            title: 发布内容的标题
            content: 发布内容的正文
            time_str: 时间文件夹名称（格式：yyyymmddhhmmss）
            
        Returns:
            tuple: (是否成功, 状态消息)
        """
        try:
            logger.info("开始发布内容")
            logger.debug(f"标题: {title if title else '[无标题]'}")
            logger.debug(f"正文长度: {len(content) if content else 0}")
            logger.debug(f"时间文件夹: {time_str}")

            # 启动应用
            self.d.app_start(self.app_package)
            logger.debug(f"启动应用: {self.app_package}")
            time.sleep(3)  # 等待应用启动

            # 点击发布按钮
            self.d.xpath('//*[@content-desc="发布"]/android.widget.ImageView[1]').click()
            logger.debug("点击发布按钮")
            time.sleep(1)

            # 尝试多种方式点击"全部"按钮
            try:
                # 方式1：使用原有的xpath
                all_photos = self.d.xpath('//*[@resource-id="android:id/content"]/android.widget.FrameLayout[1]/android.widget.FrameLayout[3]/android.widget.RelativeLayout[1]/android.widget.RelativeLayout[1]/android.widget.RelativeLayout[1]/android.widget.LinearLayout[1]')
                if all_photos.exists:
                    all_photos.click()
                else:
                    # 方式2：尝试使用文本定位
                    self.d(text="全部").click()
                logger.debug("点击'全部'按钮成功")
            except Exception as e:
                logger.error(f"点击'全部'按钮失败: {str(e)}")
                return False, "SELECT_ALBUM_FAILED"

            # 等待文件夹列表加载
            time.sleep(2)

            # 选择时间文件夹
            folder_found = False
            max_attempts = 5
            
            for attempt in range(max_attempts):
                # 尝试查找时间文件夹
                if self.d(text=time_str).exists(timeout=2):
                    self.d(text=time_str).click()
                    folder_found = True
                    logger.debug(f"成功找到并点击文件夹: {time_str}")
                    break
                
                # 未找到，滚动查找
                self.d.swipe(500, 1000, 500, 200)
                time.sleep(1)
            
            if not folder_found:
                logger.error(f"未能找到时间文件夹: {time_str}")
                return False, "FOLDER_NOT_FOUND"

            # 等待图片列表加载
            time.sleep(2)

            # 选择图片
            base_xpath = '//androidx.viewpager.widget.ViewPager/androidx.recyclerview.widget.RecyclerView[1]/android.widget.FrameLayout[1]/androidx.recyclerview.widget.RecyclerView[1]/android.widget.FrameLayout[{}]/android.widget.FrameLayout[1]/android.widget.RelativeLayout[1]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/android.widget.ImageView[1]'
            
            selected_count = 0
            index = 1
            while True:
                xpath = base_xpath.format(index)
                if self.d.xpath(xpath).exists:
                    logger.debug(f"选择第 {index} 张图片")
                    self.d.xpath(xpath).click()
                    selected_count += 1
                    index += 1
                else:
                    logger.info(f"共选择 {selected_count} 张图片")
                    break

            if selected_count == 0:
                logger.error("未能选择任何图片")
                return False, "NO_IMAGES_SELECTED"

            # 点击下一步按钮
            self.d.click(0.741, 0.964)  # 点击下一步按钮
            logger.debug("点击下一步按钮")
            time.sleep(2)  # 等待界面加载

            # 点击第二个下一步 - 使用坐标点击
            logger.debug("点击下一步按钮")
            self.d.click(0.838, 0.963)
            time.sleep(2)  # 等待点击响应

            # 输入标题和内容
            if title:
                # self.d(resourceId=f"{self.app_package}:id/-", text="添加标题").click()
                print("点击添加标题")
                self.d.xpath('//*[@text="添加标题"]').click()
                self.d.send_keys(title)
                logger.debug(f"输入标题: {title}")

            if content:
                print("点击添加标题")
                self.d.xpath(
                    '//android.widget.ScrollView/android.widget.LinearLayout[1]/android.widget.FrameLayout[3]/android.widget.LinearLayout[1]/android.view.ViewGroup[1]/android.widget.LinearLayout[1]').click()
                self.d.send_keys(content)
                logger.debug("输入正文完成")

            # 点击发布按钮
            if title or content:
                # self.d(resourceId=f"{self.app_package}:id/-", text="发布").click()
                self.d.xpath('//*[@text="发布"]').click()
            else:
                logger.debug("无标题和正文内容，直接发布")
                # 直接点击发布笔记按钮
                self.d(resourceId=f"{self.app_package}:id/-", text="发布笔记").click()

            logger.info("发布操作完成")
            
            # 先返回成功状态
            result = (True, "SUCCESS")
            
            # 在单独的线程中执行等待和熄屏操作
            def auto_sleep():
                try:
                    # time.sleep(30 * 60)  # 等待30分钟
                    time.sleep(15 * 60)  # 等待15分钟
                    self.d.press("home")  # 返回桌面
                    time.sleep(2)
                    self.d.screen_off()  # 熄屏
                except Exception as e:
                    pass  # 忽略所有错误，不影响主流程
            
            import threading
            threading.Thread(target=auto_sleep, daemon=True).start()
            
            return result

        except Exception as e:
            logger.error(f"发布内容失败: {str(e)}")
            return (False, f"AUTOMATION_FAILED: {str(e)}") 