package com.shangui.userhelp.aftersales.service;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;

public interface AftersalesService {

    WarrantyInfo queryWarranty(String orderId);

    ReturnInfo queryReturnStatus(String orderId);
}
