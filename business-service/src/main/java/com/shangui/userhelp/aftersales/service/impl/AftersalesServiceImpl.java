package com.shangui.userhelp.aftersales.service.impl;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;
import com.shangui.userhelp.aftersales.mapper.AftersalesMapper;
import com.shangui.userhelp.aftersales.service.AftersalesService;
import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import org.springframework.stereotype.Service;

@Service
public class AftersalesServiceImpl implements AftersalesService {

    private final AftersalesMapper aftersalesMapper;

    public AftersalesServiceImpl(AftersalesMapper aftersalesMapper) {
        this.aftersalesMapper = aftersalesMapper;
    }

    @Override
    public WarrantyInfo queryWarranty(String orderId) {
        validateOrderId(orderId);
        return aftersalesMapper.findWarranty(orderId);
    }

    @Override
    public ReturnInfo queryReturnStatus(String orderId) {
        validateOrderId(orderId);
        return aftersalesMapper.findReturnStatus(orderId);
    }

    private void validateOrderId(String orderId) {
        if (orderId == null || orderId.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "order_id 不能为空");
        }
    }
}
