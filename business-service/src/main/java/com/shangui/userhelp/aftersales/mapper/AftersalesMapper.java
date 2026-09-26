package com.shangui.userhelp.aftersales.mapper;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;

public interface AftersalesMapper {

    WarrantyInfo findWarranty(String orderId);

    ReturnInfo findReturnStatus(String orderId);
}
