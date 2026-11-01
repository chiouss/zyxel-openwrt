include $(TOPDIR)/rules.mk

PKG_NAME:=ipq-wifi-zyxel
PKG_RELEASE:=2
PKG_FLAGS:=nonshared

include $(INCLUDE_DIR)/package.mk

# Board data that OpenWrt's ipq-wifi package doesn't ship. Files are named
# board-<device>.<chip> like in the qca-wireless repository.

define Build/Compile
endef

define Package/ipq-wifi-zyxel-default
  SUBMENU:=ath10k Board-Specific Overrides
  SECTION:=firmware
  CATEGORY:=Firmware
  DEPENDS:=@(TARGET_ipq40xx||TARGET_qualcommax_ipq50xx)
endef

# 1: board file, 2: destination root, 3: firmware directory
define ipq-wifi-zyxel-install-to
	$(INSTALL_DIR) $(2)/lib/firmware/$(3)
	$(INSTALL_DATA) $(1) $(2)/lib/firmware/$(3)/board-2.bin
endef

ipq-wifi-zyxel-dir = $(strip \
	$(if $(filter .qca4019,$(1)),ath10k/QCA4019/hw1.0) \
	$(if $(filter .ipq5018,$(1)),ath11k/IPQ5018/hw1.0) \
	$(if $(filter .qcn6122,$(1)),ath11k/QCN6122/hw1.0) \
	$(if $(filter .qcn9074,$(1)),ath11k/QCN9074/hw1.0))

define ipq-wifi-zyxel-install-one
	$(if $(call ipq-wifi-zyxel-dir,$(suffix $(1))),,$(error Unknown board file suffix in $(1)))
	$(call ipq-wifi-zyxel-install-to,$(1),$(2),$(call ipq-wifi-zyxel-dir,$(suffix $(1))))

endef

define generate-ipq-wifi-zyxel-package
  define Package/ipq-wifi-$(1)
    $(call Package/ipq-wifi-zyxel-default)
    TITLE:=board-2.bin Overrides for $(2)
  endef

  define Package/ipq-wifi-$(1)/description
This package supplies the board-2.bin file(s) for the $(2), which
overwrite those supplied by the ath10k/ath11k firmware packages.

Do not install it for any other device!
  endef

  define Package/ipq-wifi-$(1)/install-overlay
	$$(foreach f,$$(wildcard $(CURDIR)/files/board-$(1).*),\
		$$(call ipq-wifi-zyxel-install-one,$$(f),$$(1)))
  endef

  $$(eval $$(call BuildPackage,ipq-wifi-$(1)))
endef

$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_nwa1123acv3,Zyxel NWA1123ACv3/WAC500))
$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_nwa220ax-6e,Zyxel NWA220AX-6E))
$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_wac500h,Zyxel WAC500H))
$(eval $(call generate-ipq-wifi-zyxel-package,zyxel_wax640s-6e,Zyxel WAX640S-6E))
