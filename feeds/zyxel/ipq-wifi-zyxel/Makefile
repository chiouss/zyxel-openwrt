include $(TOPDIR)/rules.mk

PKG_NAME:=ipq-wifi-zyxel
PKG_RELEASE:=1
PKG_FLAGS:=nonshared

include $(INCLUDE_DIR)/package.mk

# Board files pending in openwrt/firmware_qca-wireless#160. Drop a board
# from here once OpenWrt's ipq-wifi package ships it.

define Build/Compile
endef

define Package/ipq-wifi-zyxel-default
  SUBMENU:=ath10k Board-Specific Overrides
  SECTION:=firmware
  CATEGORY:=Firmware
  DEPENDS:=@TARGET_ipq40xx
endef

define generate-ipq-wifi-zyxel-package
  define Package/ipq-wifi-$(1)
    $(call Package/ipq-wifi-zyxel-default)
    TITLE:=board-2.bin Overrides for $(2)
  endef

  define Package/ipq-wifi-$(1)/description
This package supplies the board-2.bin file for the $(2), which
overwrites the one supplied by ath10k-board-qca4019.

Do not install it for any other device!
  endef

  define Package/ipq-wifi-$(1)/install-overlay
	$(INSTALL_DIR) $$(1)/lib/firmware/ath10k/QCA4019/hw1.0
	$(INSTALL_DATA) ./files/board-$(1).qca4019 \
		$$(1)/lib/firmware/ath10k/QCA4019/hw1.0/board-2.bin
  endef
endef

$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_nwa1123acv3,Zyxel NWA1123ACv3/WAC500))
$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_wac500h,Zyxel WAC500H))

$(eval $(call BuildPackage,ipq-wifi-zyxel_nwa1123acv3))
$(eval $(call BuildPackage,ipq-wifi-zyxel_wac500h))
